# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Core of the imas-python interpreted IDS metadata
"""
import re
import types
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple, Type
from xml.etree.ElementTree import Element

from imas.ids_coordinates import IDSCoordinate
from imas.ids_data_type import IDSDataType
from imas.ids_identifiers import IDSIdentifier, identifiers
from imas.ids_path import IDSPath


class IDSType(Enum):
    """Data dictionary indication of the time-variation character of a DD node

    The Data Model distinguishes between categories of data according to their
    time-variation. ``constant`` data are data which are not varying within the context
    of the data being referred to (e.g. pulse, simulation, calculation); ``static`` data
    are likely to be constant over a wider range (e.g. nominal coil positions during
    operation); ``dynamic`` data are those which vary in time within the context of the
    data.

    As in the Python HLI, imas-python only distinguishes between dynamic and non-dynamic
    nodes.
    """

    NONE = None
    """The DD node has no type attribute.
    """

    DYNAMIC = "dynamic"
    """Data that is varying in time.
    """

    CONSTANT = "constant"
    """Data that does not vary within the IDS.
    """

    STATIC = "static"
    """Data that does not vary between multiple IDSs.
    """

    def __init__(self, name):
        self.is_dynamic = name == "dynamic"


# This cache is for IDSMetadata for IDS toplevels
# Typical use case is one or two DD versions
# Currently the DD has ~70 unique IDSs, so this cache has plenty of size to store all
# IDSs of two DD versions.
#
# Perhaps the cache could be smaller, but that would be less efficient for the unit
# tests...
@lru_cache(maxsize=256)
def get_toplevel_metadata(structure_xml: Element) -> "IDSMetadata":
    """Build metadata tree of an IDS toplevel element.

    Args:
        structure_xml: XML element belonging to an IDS toplevel (e.g. core_profiles).
    """
    if not _type_map:
        _build_type_map()

    # Delete the custom __setattr__ so __init__ can assign values:
    orig_setattr = IDSMetadata.__setattr__
    del IDSMetadata.__setattr__
    try:
        return IDSMetadata(structure_xml, "", None)
    finally:
        # Always restore the custom __setattr__ to avoid accidental data changes
        IDSMetadata.__setattr__ = orig_setattr


_type_map: Dict[Tuple[IDSDataType, int], Type] = {}
"""Map of IDSDataType and ndim to IDSBase implementation class."""


def _build_type_map():
    """Populate _type_map.

    This must be done in a separate function to avoid circular imports.
    """
    from imas.ids_primitive import (
        IDSComplex0D,
        IDSFloat0D,
        IDSInt0D,
        IDSNumericArray,
        IDSString0D,
        IDSString1D,
    )
    from imas.ids_struct_array import IDSStructArray
    from imas.ids_structure import IDSStructure
    from imas.ids_toplevel import IDSToplevel

    _type_map[(None, 0)] = IDSToplevel
    _type_map[(IDSDataType.STRUCTURE, 0)] = IDSStructure
    _type_map[(IDSDataType.STRUCT_ARRAY, 1)] = IDSStructArray
    _type_map[(IDSDataType.STR, 0)] = IDSString0D
    _type_map[(IDSDataType.STR, 1)] = IDSString1D
    _type_map[(IDSDataType.INT, 0)] = IDSInt0D
    _type_map[(IDSDataType.FLT, 0)] = IDSFloat0D
    _type_map[(IDSDataType.CPX, 0)] = IDSComplex0D
    for dim in range(1, 7):
        _type_map[(IDSDataType.INT, dim)] = IDSNumericArray
        _type_map[(IDSDataType.FLT, dim)] = IDSNumericArray
        _type_map[(IDSDataType.CPX, dim)] = IDSNumericArray


class IDSMetadata:
    """Container for IDS Metadata stored in the Data Dictionary.

    Metadata is everything saved in the attributes of variables in IDSDef.xml.
    This includes for example documentation, its units, and coordinates.

    Metadata of structure (and array of structures) child nodes can be obtained with the
    indexing operator:

    .. code-block:: python

        core_profiles = imas.IDSFactory().core_profiles()
        # Get the metadata of the time child of the profiles_1d array of structures
        p1d_time_meta = core_profiles.metadata["profiles_1d/time"]

    Note:
        This class should not be instantiated directly, use
        :func:`get_toplevel_metadata` instead.
    """

    def __init__(
        self,
        structure_xml: Element,
        context_path: str,
        parent_meta: Optional["IDSMetadata"],
    ) -> None:
        attrib = structure_xml.attrib
        self._structure_xml = structure_xml
        self._parent = parent_meta

        # Mandatory attributes
        self.name: str = attrib["name"]
        """Name of the IDS node, for example ``"comment"``."""

        # Context path: path relative to the nearest Array of Structures
        if parent_meta is None:  # Toplevel IDS
            self._ctx_path = ""
        elif context_path:
            self._ctx_path = f"{context_path}/{self.name}"
        else:
            self._ctx_path = self.name

        # These are special and used in imas-python logic,
        # so we need to ensure proper values
        maxoccur = attrib.get("maxoccur", "unbounded")
        self.maxoccur: Optional[int] = (
            None if maxoccur == "unbounded" else int(maxoccur)
        )
        """Maximum number of occurrences allowed in the MDS+ backend. Applies to IDS
        toplevels and Arrays of Structures."""
        self.data_type: IDSDataType
        """Data type of the IDS node."""
        self.ndim: int
        """Number of dimensions (rank) of the IDS node."""
        self.data_type, self.ndim = IDSDataType.parse(attrib.get("data_type", None))
        self.path_string: str = attrib.get("path", "")  # IDSToplevel has no path
        """Path of this IDS node from the IDS toplevel, for example
        ``"ids_properties/comment"``."""
        self.path: IDSPath = IDSPath(self.path_string)
        """Parsed path of this IDS node from the IDS toplevel, see also
        :py:attr:`path_string`."""
        self.path_doc: str = attrib.get("path_doc", "")  # IDSToplevel has no path
        """Path of this IDS node from the IDS toplevel, as shown in the Data Dictionary
        documentation. For example ``"time_slice(itime)/profiles_2d(i1)/r(:,:)"``."""
        self.type: IDSType = IDSType(attrib.get("type", None))
        """Type of the IDS node, indicating if this node is time dependent. Possible
        values are ``dynamic`` (i.e. time-dependent), ``constant`` and ``static``."""
        self.timebasepath = attrib.get("timebasepath", "")
        self.units: str = attrib.get("units", "")
        """Units of this IDS node. For example ``"m.s^-2"``."""
        if self.units == "as_parent" and parent_meta is not None:
            self.units = parent_meta.units
        self.documentation = attrib.get("documentation", None)
        """Data dictionary-provided documentation for this IDS node."""

        # timebasepath is not always defined in the DD XML, mainly not for struct_arrays
        # Also, when it is defined, it may not be correct (DD 3.39.0)
        if self.data_type is IDSDataType.STRUCT_ARRAY:
            # https://git.iter.org/projects/IMAS/repos/access-layer/browse/pythoninterface/py_ids.xsl?at=refs%2Ftags%2F4.11.4#367-384
            if self.type.is_dynamic:
                self.timebasepath = self._ctx_path + "/time"
            else:
                self.timebasepath = ""
        else:  # IDSPrimitive
            # https://git.iter.org/projects/IMAS/repos/access-layer/browse/pythoninterface/py_ids.xsl?at=refs%2Ftags%2F4.11.4#1524-1566
            if self.timebasepath and (
                not self.type.is_dynamic or self._parent._is_dynamic
            ):
                self.timebasepath = ""
        self._is_dynamic = False
        if self._parent is not None:
            self._is_dynamic = self.type.is_dynamic or self._parent._is_dynamic

        self.coordinates: "tuple[IDSCoordinate]"
        """Tuple of coordinates of this node.

        ``coordinates[0]`` is the coordinate of the first dimension, etc."""
        self.coordinates_same_as: "tuple[IDSCoordinate]"
        """Indicates quantities which share the same coordinate in a given dimension,
        but the coordinate is not explicitly stored in the IDS."""
        if self.ndim == 0:
            self.coordinates = ()
            self.coordinates_same_as = ()
        else:
            # Parse coordinates
            coors = [IDSCoordinate("")] * self.ndim
            coors_same_as = [IDSCoordinate("")] * self.ndim
            for dim in range(self.ndim):
                coor = f"coordinate{dim + 1}"
                if coor in attrib:
                    coors[dim] = IDSCoordinate(attrib[coor])
                    setattr(self, coor, coors[dim])
                if coor + "_same_as" in attrib:
                    coors_same_as[dim] = IDSCoordinate(attrib[coor + "_same_as"])
                    setattr(self, coor + "_same_as", coors_same_as[dim])
            self.coordinates = tuple(coors)
            self.coordinates_same_as = tuple(coors_same_as)

        # Parse alternative coordinates
        self.alternative_coordinates: "tuple[IDSPath]" = ()
        """Quantities that can be used as coordinate instead of this node."""
        if "alternative_coordinate1" in attrib:
            self.alternative_coordinates = tuple(
                IDSPath(coor) for coor in attrib["alternative_coordinate1"].split(";")
            )

        # Store any remaining attributes from the DD XML
        for attr_name in attrib:
            if attr_name not in self.__dict__ and not attr_name.startswith("_"):
                self.__dict__[attr_name] = attrib[attr_name]

        # Cache children in a read-only dict
        ctx_path = "" if self.data_type is IDSDataType.STRUCT_ARRAY else self._ctx_path
        self._children = types.MappingProxyType(
            {
                xml_child.get("name"): IDSMetadata(xml_child, ctx_path, self)
                for xml_child in structure_xml
            }
        )

        # Cache node type
        self._node_type: Type = _type_map[self.data_type, self.ndim]
        # AL expects ndim of STR types to be one more (STR_0D is 1D array of chars)
        self._al_ndim = self.ndim + (self.data_type is IDSDataType.STR)

    def __repr__(self) -> str:
        return f"<IDSMetadata for '{self.name}'>"

    def __setattr__(self, name: str, value: Any) -> None:
        raise RuntimeError("Cannot set attribute: IDSMetadata is read-only.")

    def __delattr__(self, name: str) -> None:
        raise RuntimeError("Cannot delete attribute: IDSMetadata is read-only.")

    def __copy__(self) -> "IDSMetadata":
        return self  # IDSMetadata is immutable

    def __deepcopy__(self, memo: dict) -> "IDSMetadata":
        return self  # IDSMetadata is immutable

    def __iter__(self) -> Iterator["IDSMetadata"]:
        return iter(self._children.values())

    def __getitem__(self, path) -> "IDSMetadata":
        item = self
        for part in re.split("[./]", path):
            try:
                item = item._children[part]
            except KeyError:
                raise KeyError(
                    f"Invalid path '{path}', '{item.name}' does not have a "
                    f"'{part}' element."
                ) from None
        return item

    @property
    def identifier_enum(self) -> Optional[Type[IDSIdentifier]]:
        """The identifier enum for this IDS node (if available).

        This property is an identifier enum (a subclass of
        :py:class:`imas.ids_identifiers.IDSIdentifier`) if this node represents an
        identifier, and the Data Dictionary defines the allowed identifier values.

        This property is ``None`` when this node is not an identifier, or the Data
        Dictionary does not define the allowed identifier values.

        .. seealso:: :ref:`Identifiers`
        """
        doc_identifier = getattr(self, "doc_identifier", None)
        if not doc_identifier:
            return None
        identifier_name = Path(doc_identifier).stem
        return identifiers[identifier_name]
