from typing import Iterator, List, Optional, Tuple

from imas.ids_base import IDSBase
from imas.ids_data_type import IDSDataType
from imas.ids_metadata import IDSMetadata
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure
from imas.ids_toplevel import IDSToplevel


def _split_on_aos(metadata: IDSMetadata):
    """Split paths per IDS."""
    paths = []
    curpath = metadata.name

    item = metadata
    while item._parent.data_type is not None:
        item = item._parent
        if item.data_type is IDSDataType.STRUCT_ARRAY:
            paths.append(curpath)
            curpath = item.name
        else:
            curpath = f"{item.name}/{curpath}"
    paths.append(curpath)
    return paths[::-1]


IndexedNode = Tuple[Tuple[int, ...], IDSBase]


def indexed_tree_iter(
    ids: IDSToplevel, metadata: Optional[IDSMetadata] = None
) -> Iterator[IndexedNode]:
    """Tree iterator that tracks indices of all ancestor array of structures.

    Args:
        ids: IDS top level element to iterate over
        metadata: Iterate over all nodes inside the IDS at the metadata object.
            If ``None``, all filled items in the IDS are iterated over.

    Yields:
        (aos_indices, node) for all filled nodes.

    Example:
        >>> ids = imas.IDSFactory().new("core_profiles")
        >>> ids.profiles_1d.resize(2)
        >>> ids.profiles_1d[0].time = 1.0
        >>> ids.profiles_1d[1].t_i_average = [1.0]
        >>> list(indexed_tree_iter(ids))
        [
            ((), <IDSStructArray (IDS:core_profiles, profiles_1d with 2 items)>),
            ((0,), <IDSFloat0D (IDS:core_profiles, profiles_1d[0]/time, FLT_0D)>),
            ((1,), <IDSNumericArray (IDS:core_profiles, profiles_1d[1]/t_i_average, FLT_1D)>)
        ]
        >>> list(indexed_tree_iter(ids, ids.metadata["profiles_1d/time"]))
        [
            ((0,), <IDSFloat0D (IDS:core_profiles, profiles_1d[0]/time, FLT_0D)>),
            ((1,), <IDSFloat0D (IDS:core_profiles, profiles_1d[1]/time, empty FLT_0D)>)
        ]
    """  # noqa: E501
    if metadata is None:
        # Iterate over all filled nodes in the IDS
        yield from _full_tree_iter(ids, ())

    else:
        paths = _split_on_aos(metadata)
        if len(paths) == 1:
            yield (), ids[paths[0]]
        else:
            yield from _tree_iter(ids, paths, ())


def _tree_iter(
    structure: IDSStructure, paths: List[str], curindex: Tuple[int, ...]
) -> Iterator[IndexedNode]:
    aos_path, *paths = paths
    aos = structure[aos_path]

    if len(paths) == 1:
        path = paths[0]
        for i, node in enumerate(aos):
            yield curindex + (i,), node[path]

    else:
        for i, node in enumerate(aos):
            yield from _tree_iter(node, paths, curindex + (i,))


def _full_tree_iter(
    node: IDSStructure, cur_index: Tuple[int, ...]
) -> Iterator[IndexedNode]:
    for child in node.iter_nonempty_():
        yield (cur_index, child)
        if isinstance(child, IDSStructArray):
            for i in range(len(child)):
                yield from _full_tree_iter(child[i], cur_index + (i,))
        elif isinstance(child, IDSStructure):
            yield from _full_tree_iter(child, cur_index)
