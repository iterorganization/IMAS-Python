# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Logic to convert core/edge IDSs to their corresponding plasma ID."""

from packaging.version import Version

from imas.ids_toplevel import IDSToplevel
from imas.ids_factory import IDSFactory
from imas.exception import IDSNameError
from imas.ids_convert import DDVersionMap, NBCPathMap, _copy_structure


def convert_to_plasma_profiles(
    core_or_edge_profiles: IDSToplevel, *, deepcopy: bool = False
) -> IDSToplevel:
    """Convert a core_profiles or edge_profiles IDS to a plasma_profiles IDS.

    The input IDS must use a Data Dictionary version for which the plasma_profiles IDS
    exists (3.42.0 or newer).

    Args:
        core_or_edge_profiles: The core_profiles or edge_profiles IDS to be converted.

    Keyword Args:
        deepcopy: When True, performs a deep copy of all data. When False (default),
            numpy arrays are not copied and the converted IDS shares the same underlying
            data buffers.
    """
    return _convert_to_plasma(core_or_edge_profiles, "profiles", deepcopy)


def convert_to_plasma_sources(
    core_or_edge_sources: IDSToplevel, *, deepcopy: bool = False
) -> IDSToplevel:
    """Convert a core_sources or edge_sources IDS to a plasma_sources IDS.

    The input IDS must use a Data Dictionary version for which the plasma_sources IDS
    exists (3.42.0 or newer).

    Args:
        core_or_edge_sources: The core_sources or edge_sources IDS to be converted.

    Keyword Args:
        deepcopy: When True, performs a deep copy of all data. When False (default),
            numpy arrays are not copied and the converted IDS shares the same underlying
            data buffers.
    """
    return _convert_to_plasma(core_or_edge_sources, "sources", deepcopy)


def convert_to_plasma_transport(
    core_or_edge_transport: IDSToplevel, *, deepcopy: bool = False
) -> IDSToplevel:
    """Convert a core_transport or edge_transport IDS to a plasma_transport IDS.

    The input IDS must use a Data Dictionary version for which the plasma_transport IDS
    exists (3.42.0 or newer).

    Args:
        core_or_edge_transport: The core_transport or edge_transport IDS to be
            converted.

    Keyword Args:
        deepcopy: When True, performs a deep copy of all data. When False (default),
            numpy arrays are not copied and the converted IDS shares the same underlying
            data buffers.
    """
    return _convert_to_plasma(core_or_edge_transport, "transport", deepcopy)


class _CoreEdgePlasmaMap(DDVersionMap):
    """Subclass of DDVersionMap to generate an NBCPathMap that is suitable to copy
    between a core/edge IDS and the corresponding plasma IDS."""

    def __init__(self, source, target, factory):
        self.ids_name = source
        self.old_version = factory._etree
        self.new_version = factory._etree
        self.version_old = Version(factory.version)

        self.old_to_new = NBCPathMap()
        self.new_to_old = NBCPathMap()

        old_ids_object = factory._etree.find(f"IDS[@name='{source}']")
        new_ids_object = factory._etree.find(f"IDS[@name='{target}']")
        self._build_map(old_ids_object, new_ids_object)


def _convert_to_plasma(source: IDSToplevel, suffix: str, deepcopy: bool) -> IDSToplevel:
    # Sanity checks for input data
    if not isinstance(source, IDSToplevel):
        raise TypeError(
            f"First argument to convert_to_plasma_{suffix} must be a core_{suffix} or "
            f"edge_{suffix} of type IDSToplevel. Got a type {type(source)} instead."
        )
    if source.metadata.name not in [f"core_{suffix}", f"edge_{suffix}"]:
        raise ValueError(
            f"First argument to convert_to_plasma_{suffix} must be a core_{suffix} or "
            f"edge_{suffix} IDS. Got a {source.metadata.name} IDS instead."
        )
    if source._lazy:
        raise NotImplementedError(
            "IDS conversion is not implemented for lazy-loaded IDSs"
        )

    # Construct target plasma_{suffix} IDS
    factory: IDSFactory = source._parent
    try:
        target = factory.new(f"plasma_{suffix}")
    except IDSNameError:
        raise ValueError(
            f"Cannot convert {source.metadata.name} IDS to plasma_{suffix}: the source "
            f"IDS uses Data Dictionary version {factory.dd_version} which doesn't have "
            f"a plasma_{suffix} IDS. Please convert the source IDS to a supported Data "
            "Dictionary version using `imas.convert_ids` and try again."
        ) from None

    # Leverage existing logic from ids_convert to do the copying
    # First construct a map (to handle missing items in the target IDS)
    data_map = _CoreEdgePlasmaMap(source.metadata.name, target.metadata.name, factory)
    path_map = data_map.old_to_new  # old = core/edge, new = plasma IDS
    _copy_structure(source, target, deepcopy, path_map)

    return target
