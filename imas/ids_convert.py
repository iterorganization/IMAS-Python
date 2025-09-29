# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Functionality for converting IDSToplevels between DD versions."""

import copy
import datetime
import logging
from functools import lru_cache, partial
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple
from xml.etree.ElementTree import Element, ElementTree

import numpy
from packaging.version import InvalidVersion, Version
from scipy.interpolate import interp1d

import imas
from imas.dd_zip import parse_dd_version, dd_etree
from imas.ids_base import IDSBase
from imas.ids_data_type import IDSDataType
from imas.ids_defs import IDS_TIME_MODE_HETEROGENEOUS
from imas.ids_factory import IDSFactory
from imas.ids_path import IDSPath
from imas.ids_primitive import IDSNumeric0D, IDSNumericArray, IDSPrimitive, IDSString0D
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure
from imas.ids_toplevel import IDSToplevel

logger = logging.getLogger(__name__)
# Store for which paths we already emitted a warning that the target could not be found
# to prevent polluting the output with lots of repeated items.
_missing_paths_warning = set()


def iter_parents(path: str) -> Iterator[str]:
    """Iterate over parents of this path, starting with the highest-level parent.

    Example:
        >>> list(iter_parents("abc/def/ghi"))
        ["abc", "abc/def"]

    Args:
        path: Path to get parents of.

    Yields:
        Parent paths of the provided path.
    """
    i_slash = path.find("/")
    while i_slash != -1:
        yield path[:i_slash]
        i_slash = path.find("/", i_slash + 1)


class NBCPathMap:
    """Object mapping paths in one DD version to path, timebasepath and context path."""

    def __init__(self) -> None:
        self.path: Dict[str, Optional[str]] = {}
        """Dictionary mapping the ids path

        - When no changes have occurred (which is assumed to be the default case), the
          path is not present in the dictionary.
        - When an element is renamed it maps the old to the new name (and vice versa).
        - When an element does not exist in the other version, it is mapped to None.
        """

        self.tbp: Dict[str, str] = {}
        """Map providing the timebasepath for renamed elements."""

        self.ctxpath: Dict[str, str] = {}
        """Map providing the lowlevel context path for renamed elements."""

        self.type_change: Dict[str, Optional[Callable[[IDSBase, IDSBase], None]]] = {}
        """Dictionary of paths that had a type change.

        Type changes are mapped to None in :py:attr:`path`, this ``dict`` allows to
        distinguish between a type change and a removed node.

        Optionally, a function can be set to the path. This function can be called to
        perform a supported conversion between the new and old type (or vice versa).
        """

        self.post_process: Dict[str, Callable[[IDSBase], None]] = {}
        """Map providing postprocess functions for paths.

        The postprocess function should be applied to the nodes after all the data is
        converted.
        """

        self.post_process_ids: List[
            Callable[[IDSToplevel, IDSToplevel, bool], None]
        ] = []
        """Postprocess functions to be applied to the whole IDS.

        These postprocess functions should be applied to the whole IDS after all data is
        converted. The arguments supplied are: source IDS, target IDS, deepcopy boolean.
        """

        self.ignore_missing_paths: Set[str] = set()
        """Set of paths that should not be logged when data is present."""

    def __setitem__(self, path: str, value: Tuple[Optional[str], str, str]) -> None:
        self.path[path], self.tbp[path], self.ctxpath[path] = value

    def __contains__(self, path: str) -> bool:
        return path in self.path

    def __iter__(self) -> Iterator[str]:
        return iter(self.path)


# Expected typical use case is conversion between two versions only. With 74 IDSs
# (DD 3.39.0) a cache of 128 items should be big enough.
@lru_cache(maxsize=128)
def _DDVersionMap(*args) -> "DDVersionMap":
    return DDVersionMap(*args)


class DDVersionMap:
    """Mapping of an IDS between two Data Dictionary versions."""

    RENAMED_DESCRIPTIONS = {"aos_renamed", "leaf_renamed", "structure_renamed"}
    """Supported ``nbc_description`` values for renames."""
    STRUCTURE_TYPES = {"structure", "struct_array"}
    """Data dictionary ``data_type`` corresponding to structure-like types."""

    def __init__(
        self,
        ids_name: str,
        old_version: ElementTree,
        new_version: ElementTree,
        version_old: Version,
    ):
        self.ids_name = ids_name
        self.old_version = old_version
        self.new_version = new_version
        self.version_old = version_old

        self.old_to_new = NBCPathMap()
        self.new_to_old = NBCPathMap()

        old_ids_object = old_version.find(f"IDS[@name='{ids_name}']")
        new_ids_object = new_version.find(f"IDS[@name='{ids_name}']")
        if old_ids_object is None or new_ids_object is None:
            raise ValueError(
                f"Cannot find IDS {ids_name} in the provided DD definitions."
            )
        self._build_map(old_ids_object, new_ids_object)

    def _check_data_type(self, old_item: Element, new_item: Element):
        """Check if data type hasn't changed.

        Record paths in mapping if data type change is unsupported.

        Returns:
            True iff the data type of both items are the same.
        """
        new_data_type = new_item.get("data_type")
        old_data_type = old_item.get("data_type")
        if IDSDataType.parse(new_data_type) == IDSDataType.parse(old_data_type):
            return True

        # Data type changed, record in type_change sets
        new_path = new_item.get("path")
        old_path = old_item.get("path")
        assert new_path is not None
        assert old_path is not None

        # Check if we (maybe) support this type change
        data_types = sorted([new_data_type, old_data_type])
        if data_types == ["struct_array", "structure"]:
            self.new_to_old.type_change[new_path] = _type_changed_structure_aos
            self.old_to_new.type_change[old_path] = _type_changed_structure_aos
        elif data_types in (
            ["INT_0D", "INT_1D"],
            ["FLT_0D", "FLT_1D"],
            ["CPX_0D", "CPX_1D"],
            ["STR_0D", "STR_1D"],
        ):
            self.new_to_old.type_change[new_path] = _type_changed_0d_1d_data
            self.old_to_new.type_change[old_path] = _type_changed_0d_1d_data
        elif old_data_type == "INT_1D" and new_item.get("doc_identifier"):
            # DD3to4: Support change of grid_ggd/grid/space/coordinates_type from an
            # INT_1D to a proper identifier
            self.new_to_old.type_change[new_path] = _type_changed_to_identifier
            self.old_to_new.type_change[old_path] = _type_changed_to_identifier
        elif data_types == ["FLT_0D", "INT_0D"]:
            # Support conversion of FLT_0D -> INT_0D when the float is integral
            self.new_to_old.type_change[new_path] = _type_changed_flt0d_int0d
            self.old_to_new.type_change[old_path] = _type_changed_flt0d_int0d
        else:
            logger.debug(
                "Data type of %s changed from %s to %s. This change is not "
                "supported by IMAS-Python: no conversion will be done.",
                new_item.get("path"),
                old_item.get("data_type"),
                new_item.get("data_type"),
            )
            self.new_to_old.path[new_path] = None
            self.new_to_old.type_change[new_path] = None
            self.old_to_new.path[old_path] = None
            self.old_to_new.type_change[old_path] = None
            return False
        return True

    def _build_map(self, old: Element, new: Element) -> None:
        """Build the NBC translation map between old <-> new."""
        old_paths = {field.get("path", ""): field for field in old.iterfind(".//field")}
        new_paths = {field.get("path", ""): field for field in new.iterfind(".//field")}
        old_path_set = set(old_paths)
        new_path_set = set(new_paths)

        # expose the path->Element maps as members so other methods can reuse them
        self.old_paths = old_paths
        self.new_paths = new_paths

        def process_parent_renames(path: str) -> str:
            # Apply any parent AoS/structure rename
            # Loop in reverse order to find the closest parent which was renamed:
            for parent in reversed(list(iter_parents(path))):
                parent_rename = self.new_to_old.path.get(parent)
                if parent_rename:
                    if new_paths[parent].get("data_type") in self.STRUCTURE_TYPES:
                        path = path.replace(parent, parent_rename, 1)
                        break
            return path

        def get_old_path(path: str, previous_name: str) -> str:
            """Calculate old path from the path and change_nbc_previous_name"""
            # Apply rename
            i_slash = path.rfind("/")
            if i_slash != -1:
                old_path = path[:i_slash] + "/" + previous_name
            else:
                old_path = previous_name
            return process_parent_renames(old_path)

        # Iterate through all NBC metadata and add entries
        for new_item in new.iterfind(".//field[@change_nbc_description]"):
            new_path = new_item.get("path")
            assert new_path is not None
            nbc_description = new_item.get("change_nbc_description")
            # change_nbc_version may be a comma-separated list of versions
            # the only supported case is multiple renames in succession
            nbc_version = new_item.get("change_nbc_version")

            try:
                parsed_nbc_versions = [
                    Version(version) for version in nbc_version.split(",")
                ]
            except InvalidVersion:
                log_args = (nbc_version, new_path)
                logger.error("Ignoring invalid NBC version: %r for %r.", *log_args)
                continue
            assert sorted(parsed_nbc_versions) == parsed_nbc_versions

            if parsed_nbc_versions[-1] <= self.version_old:
                continue
            if nbc_description in DDVersionMap.RENAMED_DESCRIPTIONS:
                previous_names = new_item.get("change_nbc_previous_name").split(",")
                assert len(previous_names) == len(parsed_nbc_versions)
                # select the correct previous name:
                for i, version in enumerate(parsed_nbc_versions):
                    if version > self.version_old:
                        previous_name = previous_names[i]
                        break
                old_path = get_old_path(new_path, previous_name)
                old_item = old_paths.get(old_path)
                if old_item is None:
                    logger.debug(
                        "Skipped NBC change for %r: renamed path %r not found in %s.",
                        new_path,
                        old_path,
                        self.version_old,
                    )
                elif self._check_data_type(old_item, new_item):
                    # use class helper to register simple renames and
                    # reciprocal mappings
                    self._add_rename(old_path, new_path)
                    if old_item.get("data_type") in DDVersionMap.STRUCTURE_TYPES:
                        # Add entries for common sub-elements
                        for path in old_paths:
                            if path.startswith(old_path):
                                npath = path.replace(old_path, new_path, 1)
                                if npath in new_path_set:
                                    self._add_rename(path, npath)
            elif nbc_description == "type_changed":
                pass  # We will handle this (if possible) in self._check_data_type
            elif nbc_description == "repeat_children_first_point":
                old_path = process_parent_renames(new_path)
                self.new_to_old.post_process[new_path] = _remove_last_point
                self.old_to_new.post_process[old_path] = _repeat_first_point
            elif nbc_description == "repeat_children_first_point_conditional":
                # This conversion needs access to the old data structure to get the
                # DDv3 `closed` node which is removed in DDv4, so we handle it as a type
                # change:
                old_path = process_parent_renames(new_path)
                self.new_to_old.type_change[new_path] = _remove_last_point_conditional
                self.old_to_new.type_change[old_path] = _repeat_first_point_conditional
                self.old_to_new.ignore_missing_paths.add(f"{old_path}/closed")
            elif nbc_description in (
                "repeat_children_first_point_conditional_sibling",
                "repeat_children_first_point_conditional_sibling_dynamic",
            ):
                old_path = process_parent_renames(new_path)
                self.new_to_old.type_change[new_path] = _remove_last_point_conditional
                self.old_to_new.type_change[old_path] = _repeat_first_point_conditional
                closed_path = Path(old_path).parent / "closed"
                self.old_to_new.ignore_missing_paths.add(str(closed_path))
            elif nbc_description == "remove_last_point_if_open_annular_centreline":
                old_path = process_parent_renames(new_path)
                self.new_to_old.type_change[new_path] = _repeat_last_point_centreline
                self.old_to_new.type_change[old_path] = _remove_last_point_centreline
                closed_path = Path(old_path) / "closed"
                self.old_to_new.ignore_missing_paths.add(str(closed_path))
            else:  # Ignore unknown NBC changes
                log_args = (nbc_description, new_path)
                logger.error("Ignoring unsupported NBC change: %r for %r.", *log_args)

        # Check if all common elements are still valid
        for common_path in old_path_set & new_path_set:
            if common_path in self.new_to_old or common_path in self.old_to_new:
                continue  # This path is part of an NBC change, we can skip it
            self._check_data_type(old_paths[common_path], new_paths[common_path])

        # Record missing items
        self._map_missing(True, new_path_set.difference(old_path_set, self.new_to_old))
        self._map_missing(False, old_path_set.difference(new_path_set, self.old_to_new))

        new_version = None
        new_version_node = self.new_version.find("version")
        if new_version_node is not None:
            new_version = parse_dd_version(new_version_node.text)
        # Additional conversion rules for DDv3 to DDv4
        if self.version_old.major == 3 and new_version and new_version.major == 4:
            self._apply_3to4_conversion(old, new)

    def _add_rename(self, old_path: str, new_path: str) -> None:
        """Register a simple rename from old_path -> new_path using the
        path->Element maps stored on the instance (self.old_paths/self.new_paths).
        This will also add the reciprocal mapping when possible.
        """
        old_item = self.old_paths[old_path]
        new_item = self.new_paths[new_path]

        # forward mapping
        self.old_to_new[old_path] = (
            new_path,
            _get_tbp(new_item, self.new_paths),
            _get_ctxpath(new_path, self.new_paths),
        )

        # reciprocal mapping
        self.new_to_old[new_path] = (
            old_path,
            _get_tbp(old_item, self.old_paths),
            _get_ctxpath(old_path, self.old_paths),
        )

    def _apply_3to4_conversion(self, old: Element, new: Element) -> None:
        # Postprocessing for COCOS definition change:
        cocos_paths = []
        for psi_like in ["psi_like", "dodpsi_like"]:
            xpath_query = f".//field[@cocos_label_transformation='{psi_like}']"
            for old_item in old.iterfind(xpath_query):
                cocos_paths.append(old_item.get("path"))
        # Sign flips not covered by the generic rule:
        cocos_paths.extend(_3to4_sign_flip_paths.get(self.ids_name, []))
        for old_path in cocos_paths:
            new_path = self.old_to_new.path.get(old_path, old_path)
            self.new_to_old.post_process[new_path] = _cocos_change
            self.old_to_new.post_process[old_path] = _cocos_change

        # Convert equilibrium boundary_separatrix and populate contour_tree
        if self.ids_name == "equilibrium":
            self.old_to_new.post_process_ids.append(_equilibrium_boundary_3to4)
            self.old_to_new.ignore_missing_paths |= {
                "time_slice/boundary_separatrix",
                "time_slice/boundary_secondary_separatrix",
            }
        # Definition change for pf_active circuit/connections
        if self.ids_name == "pf_active":
            path = "circuit/connections"
            self.new_to_old.post_process[path] = _circuit_connections_4to3
            self.old_to_new.post_process[path] = _circuit_connections_3to4

        # Migrate ids_properties/source to ids_properties/provenance
        # Only implement forward conversion (DD3 -> 4):
        # - Pretend that this is a rename from ids_properties/source -> provenance
        # - And register type_change handler which will be called with the source
        #   element and the new provenance structure
        path = "ids_properties/source"
        self.old_to_new.path[path] = "ids_properties/provenance"
        self.old_to_new.type_change[path] = _ids_properties_source

        # GH#55: add logic to migrate some obsolete nodes in DD3.42.0 -> 4.0
        # These nodes (e.g. equilibrium profiles_1d/j_tor) have an NBC rename rule
        # (to e.g. equilibrium profiles_1d/j_phi) applying to DD 3.41 and older.
        # In DD 3.42, both the old AND new node names are present.
        if self.version_old.minor >= 42:  # Only apply for DD 3.42+ -> DD 4
            # Get a rename map for 3.41 -> new version
            factory341 = imas.IDSFactory("3.41.0")
            if self.ids_name in factory341.ids_names():  # Ensure the IDS exists in 3.41
                dd341_map = _DDVersionMap(
                    self.ids_name,
                    dd_etree("3.41.0"),
                    self.new_version,
                    Version("3.41.0"),
                )
                to_update = {}
                for path, newpath in self.old_to_new.path.items():
                    # Find all nodes that have disappeared in DD 4.x, and apply the
                    # rename rule from DD3.41 -> DD 4.x
                    if newpath is None and path in dd341_map.old_to_new:
                        self.old_to_new.path[path] = dd341_map.old_to_new.path[path]
                        # Note: path could be a structure or AoS, so we also put all
                        # child paths in our map:
                        path = path + "/"  # All child nodes will start with this
                        for p, v in dd341_map.old_to_new.path.items():
                            if p.startswith(path):
                                to_update[p] = v
                self.old_to_new.path.update(to_update)

        # GH#59: To improve further the conversion of DD3 to DD4, especially the
        # Machine Description part of the IDSs, we would like to add a 3to4 specific
        #  rule to convert any siblings name + identifier (that are not part of an
        # identifier structure, meaning that there is no index sibling) into
        # description + name. Meaning:
        #        parent/name (DD3) -> parent/description (DD4)
        #        parent/identifier (DD3) -> parent/name (DD4)
        # Only perform the mapping if the corresponding target fields exist in the
        # new DD and if we don't already have a mapping for the involved paths.
        # use self.old_paths and self.new_paths set in _build_map
        for p in self.old_paths:
            # look for name children
            if not p.endswith("/name"):
                continue
            parent = p.rsplit("/", 1)[0]
            name_path = f"{parent}/name"
            id_path = f"{parent}/identifier"
            index_path = f"{parent}/index"
            desc_path = f"{parent}/description"
            new_name_path = name_path

            # If neither 'name' nor 'identifier' existed in the old DD, skip this parent
            if name_path not in self.old_paths or id_path not in self.old_paths:
                continue
            # exclude identifier-structure (has index sibling)
            if index_path in self.old_paths:
                continue

            # Ensure the candidate target fields exist in the new DD
            if desc_path not in self.new_paths or new_name_path not in self.new_paths:
                continue

            # Map DD3 name -> DD4 description
            if name_path not in self.old_to_new.path:
                self._add_rename(name_path, desc_path)

            # Map DD3 identifier -> DD4 name
            if id_path in self.old_to_new.path:
                self._add_rename(id_path, new_name_path)

    def _map_missing(self, is_new: bool, missing_paths: Set[str]):
        rename_map = self.new_to_old if is_new else self.old_to_new
        # Find all structures which have a renamed sub-item
        structures_with_renames = set()
        for path in rename_map:
            for parent in iter_parents(path):
                structures_with_renames.add(parent)

        skipped_paths = set()
        for path in sorted(missing_paths):
            # Only mark a non-existing structure if there are no renames inside it, so a
            # structure marked in the rename_map as None can be skipped completely.
            if path not in structures_with_renames:
                # Only mark if there is no parent structure already skipped
                for parent in iter_parents(path):
                    if parent in skipped_paths:
                        break
                else:
                    skipped_paths.add(path)
        for path in skipped_paths:
            rename_map.path[path] = None


def _get_ctxpath(path: str, paths: Dict[str, Element]) -> str:
    """Get the path of the nearest parent AoS."""
    for parent_path in reversed(list(iter_parents(path))):
        if paths[parent_path].get("data_type") == "struct_array":
            return path[len(parent_path) + 1 :]
    return path  # no nearest parent AoS


def _get_tbp(element: Element, paths: Dict[str, Element]):
    """Calculate the timebasepath to use for the lowlevel."""
    if element.get("data_type") == "struct_array":
        # https://git.iter.org/projects/IMAS/repos/access-layer/browse/pythoninterface/py_ids.xsl?at=refs%2Ftags%2F4.11.4#367-384
        if element.get("type") != "dynamic":
            return ""
        # Find path of first ancestor that is an AoS
        path = element.get("path")
        assert path is not None
        return _get_ctxpath(path, paths) + "/time"
    # https://git.iter.org/projects/IMAS/repos/access-layer/browse/pythoninterface/py_ids.xsl?at=refs%2Ftags%2F4.11.4#1524-1566
    return element.get("timebasepath", "")


def dd_version_map_from_factories(
    ids_name: str, factory1: IDSFactory, factory2: IDSFactory
) -> Tuple[DDVersionMap, bool]:
    """Build a DDVersionMap from two IDSFactories."""
    assert factory1._version
    assert factory2._version
    factory1_version = parse_dd_version(factory1._version)
    factory2_version = parse_dd_version(factory2._version)
    old_version, old_factory, new_factory = min(
        (factory1_version, factory1, factory2),
        (factory2_version, factory2, factory1),
    )
    return (
        _DDVersionMap(ids_name, old_factory._etree, new_factory._etree, old_version),
        old_factory is factory1,
    )


def convert_ids(
    toplevel: IDSToplevel,
    version: Optional[str],
    *,
    deepcopy: bool = False,
    provenance_origin_uri: str = "",
    xml_path: Optional[str] = None,
    factory: Optional[IDSFactory] = None,
    target: Optional[IDSToplevel] = None,
) -> IDSToplevel:
    """Convert an IDS to the specified data dictionary version.

    Newer data dictionary versions may introduce non-backwards-compatible (NBC) changes.
    For example, the ``global_quantities.power_from_plasma`` quantity in the ``wall``
    IDS was renamed in DD version 3.31.0 to ``global_quantities.power_incident``. When
    converting from a version older than 3.31.0 to a version that is newer than that,
    this method will migrate the data.

    By default, this method performs a `shallow copy` of numerical data. All
    multi-dimensional numpy arrays from the returned IDS share their data with the
    original IDS. When performing `in-place` operations on numpy arrays, the data will
    be changed in both IDSs! If this is not desired, you may set the ``deepcopy``
    keyword argument to True.

    See also:
        :ref:`Conversion of IDSs between DD versions`.

    Args:
        toplevel: The IDS element to convert.
        version: The data dictionary version to convert to, for example "3.38.0". Must
            be None when using ``xml_path`` or ``factory``.

    Keyword Args:
        deepcopy: When True, performs a deep copy of all data. When False (default),
            numpy arrays are not copied and the converted IDS shares the same underlying
            data buffers.
        provenance_origin_uri: When nonempty, add an entry in the provenance data in
            ``ids_properties`` to indicate that this IDS has been converted, and it was
            originally stored at the given uri.
        xml_path: Path to a data dictionary XML file that should be used instead of the
            released data dictionary version specified by ``version``.
        factory: Existing IDSFactory to use for as target version.
        target: Use this IDSToplevel as target toplevel instead of creating one.
    """
    if toplevel._lazy:
        raise NotImplementedError(
            "IDS conversion is not implemented for lazy-loaded IDSs"
        )

    ids_name = toplevel.metadata.name
    if target is None:
        if factory is None:
            factory = IDSFactory(version, xml_path)
        if not factory.exists(ids_name):
            raise RuntimeError(
                f"There is no IDS with name {ids_name} in DD version {version}."
            )
        target = factory.new(ids_name)

    source_version = parse_dd_version(toplevel._version)
    target_version = parse_dd_version(target._version)
    logger.info(
        "Starting conversion of IDS %s from version %s to version %s.",
        ids_name,
        source_version,
        target_version,
    )
    global _missing_paths_warning
    _missing_paths_warning = set()  # clear for which paths we emitted a warning

    source_tree = toplevel._parent._etree
    target_tree = target._parent._etree
    if source_version > target_version:
        version_map = _DDVersionMap(ids_name, target_tree, source_tree, target_version)
        rename_map = version_map.new_to_old
    else:
        version_map = _DDVersionMap(ids_name, source_tree, target_tree, source_version)
        rename_map = version_map.old_to_new

    # Special case for DD3to4 pulse_schedule conversion
    if (
        toplevel.metadata.name == "pulse_schedule"
        and toplevel.ids_properties.homogeneous_time == IDS_TIME_MODE_HETEROGENEOUS
        and source_version < Version("3.40.0")
        and target_version >= Version("3.40.0")
    ):
        try:
            # Suppress "'.../time' does not exist in the target IDS." log messages.
            logger.addFilter(_pulse_schedule_3to4_logfilter)
            _pulse_schedule_3to4(toplevel, target, deepcopy, rename_map)
        finally:
            logger.removeFilter(_pulse_schedule_3to4_logfilter)
    else:
        _copy_structure(toplevel, target, deepcopy, rename_map)

    # Global post-processing functions
    for callback in rename_map.post_process_ids:
        callback(toplevel, target, deepcopy)

    logger.info("Conversion of IDS %s finished.", ids_name)
    if provenance_origin_uri:
        _add_provenance_entry(target, toplevel._version, provenance_origin_uri)
    return target


def _add_provenance_entry(
    target_ids: IDSToplevel, source_version: str, provenance_origin_uri: str
) -> None:
    # provenance node was added in DD 3.34.0
    if not hasattr(target_ids.ids_properties, "provenance"):
        logger.warning(
            "Cannot add provenance entry for DD conversion: "
            "target IDS does not have a provenance property."
        )
        return

    # Find the node corresponding to the whole IDS, or create one if there is none
    for node in target_ids.ids_properties.provenance.node:
        if node.path == "":
            break
    else:
        # No node found for the whole IDS, create a new one:
        curlen = len(target_ids.ids_properties.provenance.node)
        target_ids.ids_properties.provenance.node.resize(curlen + 1, keep=True)
        node = target_ids.ids_properties.provenance.node[-1]

    # Populate the node
    source_txt = (
        f"{provenance_origin_uri}; "
        f"This IDS has been converted from DD {source_version} to "
        f"DD {target_ids._dd_version} by IMAS-Python {imas.__version__}."
    )
    if hasattr(node, "reference"):
        # DD version after IMAS-5304
        node.reference.resize(len(node.reference) + 1, keep=True)
        node.reference[-1].name = source_txt
        utc = getattr(datetime, "UTC", datetime.timezone.utc)
        timestamp = datetime.datetime.now(utc).isoformat(timespec="seconds")
        node.reference[-1].timestamp = timestamp.replace("+00:00", "Z")
    else:
        # DD before IMAS-5304 (between 3.34.0 and 3.41.0)
        node.sources.append(source_txt)  # sources is a STR_1D (=list of strings)


def _get_target_item(
    item: IDSBase, target: IDSStructure, rename_map: NBCPathMap
) -> Optional[IDSBase]:
    """Find and return the corresponding target item if it exists.

    This method follows NBC renames (as stored in the rename map). It returns None if
    there is no corresponding target item in the target structure.
    """
    path = item.metadata.path_string

    # Follow NBC renames:
    if path in rename_map:
        if rename_map.path[path] is None:
            if path not in rename_map.ignore_missing_paths:
                # Only warn the first time that we encounter this path:
                if path not in _missing_paths_warning:
                    if path in rename_map.type_change:
                        msg = "Element %r changed type in the target IDS."
                    else:
                        msg = "Element %r does not exist in the target IDS."
                    logger.warning(msg + " Data is not copied.", path)
                    _missing_paths_warning.add(path)
            return None
        else:
            return IDSPath(rename_map.path[path]).goto(target)

    # No NBC renames:
    try:
        return target[item.metadata.name]
    except AttributeError:
        # In exceptional cases the item does not exist in the target. Example:
        # neutron_diagnostic IDS between DD 3.40.1 and 3.41.0. has renamed
        # synthetic_signals/fusion_power -> fusion_power. The synthetic_signals
        # structure no longer exists but we need to descend into it to get the
        # total_neutron_flux.
        return target


def _copy_structure(
    source: IDSStructure,
    target: IDSStructure,
    deepcopy: bool,
    rename_map: NBCPathMap,
    callback: Optional[Callable] = None,
):
    """Recursively copy data, following NBC renames.

    Args:
        source: Source structure.
        target: Target structure.
        deepcopy: See :func:`convert_ids`.
        source_is_new: True iff the DD version of the source is newer than that of the
            target.
        version_map: Version map containing NBC renames.
        callback: Optional callback that is called for every copied node.
    """
    for item in source.iter_nonempty_():
        path = item.metadata.path_string
        target_item = _get_target_item(item, target, rename_map)
        if target_item is None:
            continue

        if path in rename_map.type_change:
            # Handle type change
            new_items = rename_map.type_change[path](item, target_item)
            if new_items is None:
                continue  # handled
            else:
                item, target_item = new_items

        if isinstance(item, IDSStructArray):
            size = len(item)
            target_item.resize(size)
            for i in range(size):
                _copy_structure(item[i], target_item[i], deepcopy, rename_map, callback)
        elif isinstance(item, IDSStructure):
            _copy_structure(item, target_item, deepcopy, rename_map, callback)
        else:
            target_item.value = copy.copy(item.value) if deepcopy else item.value

        # Post-process the node:
        if path in rename_map.post_process:
            rename_map.post_process[path](target_item)
        if callback is not None:
            callback(item, target_item)


_3to4_sign_flip_paths = {
    "core_instant_changes": [
        "change/profiles_1d/grid/psi_magnetic_axis",
        "change/profiles_1d/grid/psi_boundary",
    ],
    "core_profiles": [
        "profiles_1d/grid/psi_magnetic_axis",
        "profiles_1d/grid/psi_boundary",
    ],
    "core_sources": [
        "source/profiles_1d/grid/psi_magnetic_axis",
        "source/profiles_1d/grid/psi_boundary",
    ],
    "core_transport": [
        "model/profiles_1d/grid_d/psi_magnetic_axis",
        "model/profiles_1d/grid_d/psi_boundary",
        "model/profiles_1d/grid_v/psi_magnetic_axis",
        "model/profiles_1d/grid_v/psi_boundary",
        "model/profiles_1d/grid_flux/psi_magnetic_axis",
        "model/profiles_1d/grid_flux/psi_boundary",
    ],
    "disruption": [
        "global_quantities/psi_halo_boundary",
        "profiles_1d/grid/psi_magnetic_axis",
        "profiles_1d/grid/psi_boundary",
    ],
    "ece": [
        "channel/beam_tracing/beam/position/psi",
        "psi_normalization/psi_magnetic_axis",
        "psi_normalization/psi_boundary",
    ],
    "edge_profiles": [
        "profiles_1d/grid/psi",
        "profiles_1d/grid/psi_magnetic_axis",
        "profiles_1d/grid/psi_boundary",
    ],
    "equilibrium": [
        "time_slice/boundary/psi",
        "time_slice/global_quantities/q_min/psi",
        "time_slice/ggd/psi/values",
    ],
    "mhd": ["ggd/psi/values"],
    "pellets": ["time_slice/pellet/path_profiles/psi"],
    "plasma_profiles": [
        "profiles_1d/grid/psi",
        "profiles_1d/grid/psi_magnetic_axis",
        "profiles_1d/grid/psi_boundary",
        "ggd/psi/values",
    ],
    "plasma_sources": [
        "source/profiles_1d/grid/psi",
        "source/profiles_1d/grid/psi_magnetic_axis",
        "source/profiles_1d/grid/psi_boundary",
    ],
    "plasma_transport": [
        "model/profiles_1d/grid_d/psi",
        "model/profiles_1d/grid_d/psi_magnetic_axis",
        "model/profiles_1d/grid_d/psi_boundary",
        "model/profiles_1d/grid_v/psi",
        "model/profiles_1d/grid_v/psi_magnetic_axis",
        "model/profiles_1d/grid_v/psi_boundary",
        "model/profiles_1d/grid_flux/psi",
        "model/profiles_1d/grid_flux/psi_magnetic_axis",
        "model/profiles_1d/grid_flux/psi_boundary",
    ],
    "radiation": [
        "process/profiles_1d/grid/psi_magnetic_axis",
        "process/profiles_1d/grid/psi_boundary",
    ],
    "reflectometer_profile": [
        "psi_normalization/psi_magnetic_axis",
        "psi_normalization/psi_boundary",
    ],
    "reflectometer_fluctuation": [
        "psi_normalization/psi_magnetic_axis",
        "psi_normalization/psi_boundary",
    ],
    "runaway_electrons": [
        "profiles_1d/grid/psi_magnetic_axis",
        "profiles_1d/grid/psi_boundary",
    ],
    "sawteeth": [
        "profiles_1d/grid/psi_magnetic_axis",
        "profiles_1d/grid/psi_boundary",
    ],
    "summary": [
        "global_quantities/psi_external_average/value",
        "local/magnetic_axis/position/psi",
    ],
    "transport_solver_numerics": [
        "solver_1d/grid/psi_magnetic_axis",
        "solver_1d/grid/psi_boundary",
        "derivatives_1d/grid/psi_magnetic_axis",
        "derivatives_1d/grid/psi_boundary",
    ],
    "wall": ["description_ggd/ggd/psi/values"],
    "waves": [
        "coherent_wave/profiles_1d/grid/psi_magnetic_axis",
        "coherent_wave/profiles_1d/grid/psi_boundary",
        "coherent_wave/profiles_2d/grid/psi",
        "coherent_wave/beam_tracing/beam/position/psi",
    ],
}
"""List of paths per IDS that require a COCOS sign change, but aren't covered by the
generic rule."""


########################################################################################
# Type changed handlers and post-processing functions                                  #
########################################################################################


def _type_changed_structure_aos(
    source_node: IDSBase, target_node: IDSBase
) -> Optional[Tuple[IDSStructure, IDSStructure]]:
    """Handle changed type, structure to array of structures (or vice versa): IMAS-5170.

    Args:
        source_node: data source (must be IDSStructure or IDSStructArray)
        target_node: data target (must be IDSStructArray or IDSStructure)

    Returns:
        (source_node, target_node): new source and target node to continue copying, or
            None if no copying needs to be done.
    """
    if isinstance(source_node, IDSStructure):
        # Structure to AOS is always supported
        assert isinstance(target_node, IDSStructArray)
        target_node.resize(1)
        return source_node, target_node[0]
    assert isinstance(source_node, IDSStructArray)
    assert len(source_node) > 0  # empty AoS should not be provided as source_node
    assert isinstance(target_node, IDSStructure)
    if len(source_node) == 1:
        # AoS to Structure is supported when the AOS has size 1
        return source_node[0], target_node
    # source_node has more than 1 element, this is not supported:
    logger.warning(
        "Element %r changed type in the target IDS and has more than 1 item. "
        "Data is not copied.",
        source_node.metadata.path_string,
    )
    return None


def _type_changed_0d_1d_data(
    source_node: IDSPrimitive, target_node: IDSPrimitive
) -> None:
    """Handle changed type, 0D to 1D (or vice versa): IMAS-5170.

    Note: underlying data type (INT, FLT, CPX or STR) should not change.

    Args:
        source_node: Data source
        target_node: Data target
    """
    if source_node.metadata.ndim == 0:
        # 0D to 1D is always supported
        target_node.value = [source_node.value]
    elif len(source_node) == 1:
        # 1D to 0D is only supported when 1 item is present
        target_node.value = source_node[0]
    else:
        logger.warning(
            "Element %r changed type in the target IDS and has more than 1 item. "
            "Data is not copied.",
            source_node.metadata.path_string,
        )


def _type_changed_to_identifier(source_node: IDSBase, target_node: IDSBase) -> None:
    """Handle a type change from list of indexes to a proper identifier."""
    if len(source_node) == 0:
        return

    if source_node.metadata.data_type is IDSDataType.INT:
        # target_node is an array of identifier structures
        target_node.resize(len(source_node))
        identifier_enum = target_node.metadata.identifier_enum
        if identifier_enum is not None:
            for i in range(len(source_node)):
                try:
                    # Look up the index in the identifier and assign to set name, index
                    # and description
                    target_node[i] = identifier_enum(source_node[i])
                except ValueError:
                    # That may fail for unknown values (e.g. negative values): fall back
                    # to only setting index and leaving name and description empty
                    target_node[i].index = source_node[i]
        else:
            # We couldn't get the identifier enum, so just copy into the index array
            for i in range(len(source_node)):
                target_node[i].index = source_node[i]

    else:
        # source_node is an array of identifier structures, target_node is an INT_1D
        target_node.value = numpy.array(
            [node.index for node in source_node], numpy.int32
        )


def _type_changed_flt0d_int0d(source_node: IDSNumeric0D, target_node: IDSNumeric0D):
    """Handle a type change from FLT_0D to INT_0D.

    Support type change of ion/element/z_n from DD3 to DD4.

    Note:
        When the floating point data cannot be converted to an integer without loss of
        data, a warning is issued and the data is not copied.
    """
    if source_node.metadata.data_type is IDSDataType.INT:
        # INT to FLT can always be represented exactly
        target_node.value = float(source_node.value)

    else:
        float_value: float = source_node.value
        int_value = numpy.int32(float_value)
        if int_value == float_value:
            target_node.value = int_value  # no data lost on conversion
        else:
            logger.warning(
                "Element %r with value %f is cannot be represented as an integer. "
                "Data is not copied.",
                source_node.metadata.path_string,
                float_value,
            )


def _remove_last_point(node: IDSBase) -> None:
    """Postprocess method for nbc_description=repeat_children_first_point.

    This method handles postprocessing when converting from new (DDv4) to old (DDv3).
    """
    for child in node.iter_nonempty_():
        child.value = child.value[:-1]


def _repeat_first_point(node: IDSBase) -> None:
    """Postprocess method for nbc_description=repeat_children_first_point.

    This method handles postprocessing when converting from old (DDv3) to new (DDv4).
    """
    for child in node.iter_nonempty_():
        child.value = numpy.concatenate((child.value, [child.value[0]]))


def _remove_last_point_conditional(
    source_node: IDSStructure, target_node: IDSStructure
) -> None:
    """Type change method for nbc_description=repeat_children_first_point_conditional*.

    This method handles converting from new (DDv4) to old (DDv3).
    """
    closed_node = getattr(target_node, "closed", None)
    if closed_node is None:  # closed is a sibling node
        closed_node = target_node._dd_parent.closed

    # Figure out if the contour is closed:
    closed = True
    # source_node may be an AoS for the ...conditional_sibling_dynamic case
    if source_node.metadata.data_type is IDSDataType.STRUCT_ARRAY:
        iterator = source_node
    else:
        iterator = [source_node]
    for source in iterator:
        for component in source.iter_nonempty_():
            if component.metadata.name != "time":
                if not numpy.isclose(component[0], component[-1], rtol=1e-6, atol=0):
                    closed = False
                    break
        if not closed:
            break

    # Copy data
    closed_node.value = int(closed)
    if source_node.metadata.data_type is IDSDataType.STRUCT_ARRAY:
        target_node.resize(len(source_node))
        iterator = zip(source_node, target_node)
    else:
        iterator = [(source_node, target_node)]
    for source, target in iterator:
        for child in source.iter_nonempty_():
            value = child.value
            if (
                closed
                and child.metadata.name != "time"
                and isinstance(child, IDSNumericArray)
            ):
                # repeat first point:
                value = value[:-1]
            target[child.metadata.name] = value


def _repeat_first_point_conditional(
    source_node: IDSStructure, target_node: IDSStructure
) -> None:
    """Type change method for nbc_description=repeat_children_first_point_conditional*.

    This method handles converting from old (DDv3) to new (DDv4).
    """
    closed_node = getattr(source_node, "closed", None)
    if closed_node is None:  # closed is a sibling node
        closed_node = source_node._dd_parent.closed
    closed = bool(closed_node)

    # source_node may be an AoS for the ...conditional_sibling_dynamic case
    if source_node.metadata.data_type is IDSDataType.STRUCT_ARRAY:
        target_node.resize(len(source_node))
        iterator = zip(source_node, target_node)
    else:
        iterator = [(source_node, target_node)]
    for source, target in iterator:
        for child in source.iter_nonempty_():
            if child.metadata.name != "closed" and not child.metadata.name.endswith(
                "_error_index"
            ):
                value = child.value
                if (
                    closed
                    and child.metadata.name != "time"
                    and isinstance(child, IDSNumericArray)
                ):
                    # repeat first point:
                    value = numpy.concatenate((value, [value[0]]))
                target[child.metadata.name] = value


def _remove_last_point_centreline(source_node: IDSBase, target_node: IDSBase) -> None:
    """Type change method for
      nbc_description=repeat_children_first_point_conditional_centreline.

    This method handles converting from old (DDv3) to new (DDv4).

    If a centreline is a closed contour, we should do nothing.
    If it is an open contour the thickness variable had too many entries,
      and we'll drop the last one.
    """
    closed = bool(source_node._parent.centreline.closed)

    if closed:
        target_node.value = source_node.value
    else:
        target_node.value = source_node.value[:-1]


def _repeat_last_point_centreline(source_node: IDSBase, target_node: IDSBase) -> None:
    """Type change method for
     nbc_description=repeat_children_first_point_conditional_centreline.

    This method handles converting from new (DDv4) to old (DDv3).

    If a centreline is a closed contour, we should do nothing.
    If it is an open contour the thickness variable in the older
     dd has one extra entry, so repeat the last one.
    """
    closed = bool(target_node._parent.centreline.closed)
    if closed:
        target_node.value = source_node.value
    else:
        target_node.value = numpy.concatenate(
            (source_node.value, [source_node.value[-1]])
        )


def _cocos_change(node: IDSBase) -> None:
    """Handle COCOS definition change: multiply values by -1."""
    if not isinstance(node, IDSPrimitive):
        if node.metadata.path_string == "flux_loop/flux":
            # Workaround for DD definition issue with flux_loop/flux in magnetics IDS
            node.data.value = -node.data.value
        else:
            logger.error(
                "Error while applying COCOS transformation (DD3->4): cannot multiply "
                "element %r by -1.",
                node.metadata.path_string,
            )
    else:
        node.value = -node.value


def _circuit_connections_3to4(node: IDSPrimitive) -> None:
    """Handle definition change for pf_active circuit/connections."""
    shape = node.shape
    if shape[1] % 2:  # second dimension not divisible by 2:
        logger.error(
            f"Error while converting {node}. Size of the second dimension should "
            "be divisible by 2. Data was not converted."
        )
    else:
        node.value = node.value[:, ::2] - node.value[:, 1::2]


def _circuit_connections_4to3(node: IDSPrimitive) -> None:
    """Handle definition change for pf_active circuit/connections."""
    shape = node.shape
    new_value = numpy.zeros((shape[0], 2 * shape[1]), dtype=numpy.int32)
    new_value[:, ::2] = node.value == 1
    new_value[:, 1::2] = node.value == -1
    node.value = new_value


def _ids_properties_source(source: IDSString0D, provenance: IDSStructure) -> None:
    """Handle DD3to4 migration of ids_properties/source to ids_properties/provenance."""
    if len(provenance.node) > 0:
        logger.warning(
            "Element %r could not be migrated: %r is alreadys set.",
            source.metadata.path_string,
            provenance.node.metadata.path_string,
        )
        return

    # Populate ids_properties/provenance/node[0]/reference[0].name with source.value
    provenance.node.resize(1)
    provenance.node[0].reference.resize(1)
    provenance.node[0].reference[0].name = source.value


def _pulse_schedule_3to4(
    source: IDSStructure,
    target: IDSStructure,
    deepcopy: bool,
    rename_map: NBCPathMap,
):
    """Recursively copy data, following NBC renames, and converting time bases for the
    pulse_schedule IDS.

    Args:
        source: Source structure.
        target: Target structure.
        deepcopy: See :func:`convert_ids`.
        rename_map: Map containing NBC renames.
    """
    # All prerequisites are checked before calling this function:
    # - source and target are pulse_schedule IDSs
    # - source has DD version < 3.40.0
    # - target has DD version >= 4.0.0, < 5.0
    # - IDS is using heterogeneous time

    for item in source.iter_nonempty_():
        name = item.metadata.name
        target_item = _get_target_item(item, target, rename_map)
        if target_item is None:
            continue

        # Special cases for non-dynamic stuff
        if name in ["ids_properties", "code"]:
            _copy_structure(item, target_item, deepcopy, rename_map)
        elif name == "time":
            target_item.value = item.value if not deepcopy else copy.copy(item.value)
        elif name == "event":
            size = len(item)
            target_item.resize(size)
            for i in range(size):
                _copy_structure(item[i], target_item[i], deepcopy, rename_map)
        else:
            # Find all time bases
            time_bases = [
                node.value
                for node in imas.util.tree_iter(item)
                if node.metadata.name == "time"
            ]
            # Construct the common time base
            timebase = numpy.unique(numpy.concatenate(time_bases)) if time_bases else []
            target_item.time = timebase
            # Do the conversion
            callback = partial(_pulse_schedule_resample_callback, timebase)
            _copy_structure(item, target_item, deepcopy, rename_map, callback)


def _pulse_schedule_3to4_logfilter(logrecord: logging.LogRecord) -> bool:
    """Suppress "'.../time' does not exist in the target IDS." log messages."""
    return not (logrecord.args and str(logrecord.args[0]).endswith("/time"))


def _pulse_schedule_resample_callback(timebase, item: IDSBase, target_item: IDSBase):
    """Callback from _copy_structure to resample dynamic data on the new timebase"""
    if item.metadata.ndim == 1 and item.metadata.coordinates[0].is_time_coordinate:
        # Interpolate 1D dynamic quantities to the common time base
        time = item.coordinates[0]
        if len(item) != len(time):
            raise ValueError(
                f"Array {item} has a different size than its time base {time}."
            )
        is_integer = item.metadata.data_type is IDSDataType.INT
        value = interp1d(
            time.value,
            item.value,
            "previous" if is_integer else "linear",
            copy=False,
            bounds_error=False,
            fill_value=(item[0], item[-1]),
            assume_sorted=True,
        )(timebase)
        target_item.value = value.astype(numpy.int32) if is_integer else value


def _equilibrium_boundary_3to4(eq3: IDSToplevel, eq4: IDSToplevel, deepcopy: bool):
    """Convert DD3 boundary[[_secondary]_separatrix] to DD4 contour_tree"""
    # Implement https://github.com/iterorganization/IMAS-Python/issues/60
    copy = numpy.copy if deepcopy else lambda x: x
    for ts3, ts4 in zip(eq3.time_slice, eq4.time_slice):
        if not ts3.global_quantities.psi_axis.has_value:
            # No magnetic axis, assume no boundary either:
            continue
        n_nodes = 1  # magnetic axis
        if ts3.boundary_separatrix.psi.has_value:
            n_nodes = 2
            if (  # boundary_secondary_separatrix is introduced in DD 3.32.0
                hasattr(ts3, "boundary_secondary_separatrix")
                and ts3.boundary_secondary_separatrix.psi.has_value
            ):
                n_nodes = 3
        node = ts4.contour_tree.node
        node.resize(n_nodes)
        # Magnetic axis (primary O-point)
        gq = ts3.global_quantities
        # Note the sign flip for psi due to the COCOS change between DD3 and DD4!
        axis_is_psi_minimum = -gq.psi_axis < -gq.psi_boundary

        node[0].critical_type = 0 if axis_is_psi_minimum else 2
        node[0].r = gq.magnetic_axis.r
        node[0].z = gq.magnetic_axis.z
        node[0].psi = -gq.psi_axis  # COCOS change

        # X-points
        if n_nodes >= 2:
            if ts3.boundary_separatrix.type == 0:  # limiter plasma
                node[1].critical_type = 2 if axis_is_psi_minimum else 0
                node[1].r = ts3.boundary_separatrix.active_limiter_point.r
                node[1].z = ts3.boundary_separatrix.active_limiter_point.z
            else:
                node[1].critical_type = 1  # saddle-point (x-point)
                if len(ts3.boundary_separatrix.x_point):
                    node[1].r = ts3.boundary_separatrix.x_point[0].r
                    node[1].z = ts3.boundary_separatrix.x_point[0].z
                # Additional x-points. N.B. levelset is only stored on the first node
                for i in range(1, len(ts3.boundary_separatrix.x_point)):
                    node.resize(len(node) + 1, keep=True)
                    node[-1].critical_type = 1
                    node[-1].r = ts3.boundary_separatrix.x_point[i].r
                    node[-1].z = ts3.boundary_separatrix.x_point[i].z
                    node[-1].psi = -ts3.boundary_separatrix.psi
            node[1].psi = -ts3.boundary_separatrix.psi  # COCOS change
            node[1].levelset.r = copy(ts3.boundary_separatrix.outline.r)
            node[1].levelset.z = copy(ts3.boundary_separatrix.outline.z)

        if n_nodes >= 3:
            node[2].critical_type = 1  # saddle-point (x-point)
            if len(ts3.boundary_secondary_separatrix.x_point):
                node[2].r = ts3.boundary_secondary_separatrix.x_point[0].r
                node[2].z = ts3.boundary_secondary_separatrix.x_point[0].z
                # Additional x-points. N.B. levelset is only stored on the first node
                for i in range(1, len(ts3.boundary_secondary_separatrix.x_point)):
                    node.resize(len(node) + 1, keep=True)
                    node[-1].critical_type = 1
                    node[-1].r = ts3.boundary_secondary_separatrix.x_point[i].r
                    node[-1].z = ts3.boundary_secondary_separatrix.x_point[i].z
                    node[-1].psi = -ts3.boundary_secondary_separatrix.psi
            node[2].psi = -ts3.boundary_secondary_separatrix.psi  # COCOS change
            node[2].levelset.r = copy(ts3.boundary_secondary_separatrix.outline.r)
            node[2].levelset.z = copy(ts3.boundary_secondary_separatrix.outline.z)
