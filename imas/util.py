# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Collection of useful helper methods when working with imas-python.
"""


import logging
import re
from typing import Any, Callable, Iterator, List, Optional, Tuple, Union

import numpy

from imas.db_entry import DBEntry
from imas.ids_base import IDSBase
from imas.ids_factory import IDSFactory
from imas.ids_metadata import IDSMetadata
from imas.ids_primitive import IDSInt0D, IDSPrimitive
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure
from imas.ids_toplevel import IDSToplevel

logger = logging.getLogger(__name__)


def visit_children(
    func: Callable,
    node: IDSBase,
    *,
    leaf_only: bool = True,
    visit_empty: bool = False,
    accept_lazy: bool = False,
) -> None:
    """Apply a function to node and its children

    imas-python objects generally live in a tree structure. Similar to Pythons
    :py:func:`map`, this method can be used to apply a function to objects
    within this tree structure.

    Args:
        func: Function to apply to each selected node.
        node: Node that function :param:`func` will be applied to.
            The function will be applied to the node itself and
            all its descendants, depending on :param:`leaf_only`.

    Keyword Args:
        leaf_only: Apply function to:

            * ``True``: Only leaf nodes, not internal nodes
            * ``False``: All nodes, including internal nodes

        visit_empty: When set to True, also apply the function to empty nodes.
        accept_lazy: See documentation of :py:param:`iter_nonempty_()
            <imas.ids_structure.IDSStructure.iter_nonempty_.accept_lazy>`. Only
            relevant when :param:`visit_empty` is False.

    Example:
        .. code-block:: python

            # Print all filled leaf nodes in a given imas-python IDSToplevel
            visit_children(print, toplevel)

    See Also:
        :func:`tree_iter` for the iterator variant of this method.
    """
    for node in tree_iter(
        node,
        leaf_only=leaf_only,
        visit_empty=visit_empty,
        accept_lazy=accept_lazy,
        include_node=True,
    ):
        func(node)


def tree_iter(
    node: IDSBase,
    *,
    leaf_only: bool = True,
    visit_empty: bool = False,
    accept_lazy: bool = False,
    include_node: bool = False,
) -> Iterator[IDSBase]:
    """Tree iterator for imas-python structures.

    Iterate (depth-first) through the whole subtree of an imas-python structure.

    Args:
        node: Node to start iterating from.

    Keyword Args:
        leaf_only: Iterate over:

            * ``True``: Only leaf nodes, not internal nodes
            * ``False``: All nodes, including internal nodes

        visit_empty: When set to True, iterate over empty nodes.
        accept_lazy: See documentation of :py:param:`iter_nonempty_()
            <imas.ids_structure.IDSStructure.iter_nonempty_.accept_lazy>`. Only
            relevant when :param:`visit_empty` is False.
        include_node: When set to True the iterator will include the provided node (if
            the node is not a leaf node, it is included only when :param:`leaf_only` is
            False).

    Example:
        .. code-block:: python

            # Iterate over all filled leaf nodes in a given imas-python IDSToplevel
            for node in tree_iter(toplevel):
                print(node)

    See Also:
        :func:`visit_children` for the functional variant of this method.
    """
    if include_node and (not leaf_only or isinstance(node, IDSPrimitive)):
        yield node
    if not isinstance(node, IDSPrimitive):
        yield from _tree_iter(node, leaf_only, visit_empty, accept_lazy)


def _tree_iter(
    node: IDSStructure, leaf_only: bool, visit_empty: bool, accept_lazy: bool
) -> Iterator[IDSBase]:
    """Implement :func:`tree_iter` recursively."""
    iterator = node
    if not visit_empty and isinstance(node, IDSStructure):
        # Only iterate over non-empty nodes
        iterator = node.iter_nonempty_(accept_lazy=accept_lazy)

    for child in iterator:
        if isinstance(child, IDSPrimitive):
            yield child
        else:
            if not leaf_only:
                yield child
            yield from _tree_iter(child, leaf_only, visit_empty, accept_lazy)


def idsdiff(struct1: IDSStructure, struct2: IDSStructure) -> None:
    """Generate a diff betweeen two IDS structures and print the result to the terminal.

    Args:
        struct1: IDS or structure within an IDS.
        struct2: IDS or structure within an IDS to compare against :param:`struct1`.
    """
    import imas._util as _util

    _util.idsdiff_impl(struct1, struct2)


Difference = Tuple[str, Any, Any]


def idsdiffgen(
    struct1: IDSStructure, struct2: IDSStructure, *, accept_lazy=False
) -> Iterator[Difference]:
    """Generate differences between two structures.

    Args:
        struct1: IDS or structure within an IDS.
        struct2: IDS or structure within an IDS to compare against :param:`struct1`.

    Keyword Args:
        accept_lazy: See documentation of :py:param:`iter_nonempty_()
            <imas.ids_structure.IDSStructure.iter_nonempty_.accept_lazy>`.

    Yields:
        (description_or_path, node1, node2): tuple describing a difference:

        - Description of the difference (e.g. ``"Data Dictionary version"``) or path
          of the IDS node.
        - Node or value from struct1.
        - Node or value from struct2.
    """
    # Compare DD versions
    if struct1._version != struct2._version:
        yield ("Data Dictionary version", struct1._version, struct2._version)
    # Compare IDS names
    if struct1._toplevel.metadata.name != struct2._toplevel.metadata.name:
        yield (
            "IDS name",
            struct1._toplevel.metadata.name,
            struct2._toplevel.metadata.name,
        )
    # Compare paths in the IDS
    if struct1.metadata.path_string != struct2.metadata.path_string:
        yield (
            "Path in IDS",
            struct1.metadata.path_string,
            struct2.metadata.path_string,
        )

    # Continue with recursively comparing values
    yield from _idsdiffgen(struct1, struct2, accept_lazy=accept_lazy)


def _idsdiffgen(
    struct1: IDSStructure, struct2: IDSStructure, *, accept_lazy=False
) -> Iterator[Difference]:
    children1 = {
        child.metadata.name: child
        for child in struct1.iter_nonempty_(accept_lazy=accept_lazy)
    }
    children2 = {
        child.metadata.name: child
        for child in struct2.iter_nonempty_(accept_lazy=accept_lazy)
    }

    for childname, child1 in children1.items():
        child2 = children2.pop(childname, None)
        if child2 is None:
            if isinstance(child1, IDSStructure):
                for child in tree_iter(child1, accept_lazy=accept_lazy):
                    yield (child.metadata.path_string, child, None)
            else:
                yield (child1.metadata.path_string, child1, None)

        elif isinstance(child1, IDSPrimitive) and isinstance(child2, IDSPrimitive):
            if not numpy.array_equal(child1.value, child2.value):
                try:
                    # NaN are equal: but this is not supported for all types
                    eq = numpy.array_equal(child1.value, child2.value, equal_nan=True)
                except TypeError:
                    # TypeError is raised when child1/child2 are not float or complex
                    eq = False
                if not eq:
                    yield (child1.metadata.path_string, child1, child2)

        elif isinstance(child1, IDSStructure) and isinstance(child2, IDSStructure):
            # Check recursively
            yield from _idsdiffgen(child1, child2, accept_lazy=accept_lazy)

        elif isinstance(child1, IDSStructArray) and isinstance(child2, IDSStructArray):
            # Compare sizes
            if len(child1) != len(child2):
                yield (child1.metadata.path_string, child1, child2)
            # Recursively compare child structures
            for c1, c2 in zip(child1, child2):
                yield from _idsdiffgen(c1, c2, accept_lazy=accept_lazy)

        else:
            yield (f"Incompatible types for {child1.metadata.path}", child1, child2)

    for child2 in children2.values():
        if isinstance(child2, IDSStructure):
            for child in tree_iter(child2, accept_lazy=accept_lazy):
                yield (child.metadata.path_string, None, child)
        else:
            yield (child2.metadata.path_string, None, child2)


def resample(node, old_time, new_time, homogeneousTime=None, inplace=False, **kwargs):
    """Resample all primitives in their time dimension to a new time array"""
    import imas._util as _util

    return _util.resample_impl(
        node, old_time, new_time, homogeneousTime, inplace, **kwargs
    )


def print_tree(structure, hide_empty_nodes=True):
    """Print the full tree of an IDS or IDS structure.

    Caution:
        With :py:param:`hide_empty_nodes` set to ``True``, lazy-loaded IDSs will only
        show loaded nodes.

    Args:
        structure: IDS structure to print
        hide_empty_nodes: Show or hide nodes without value.
    """
    import imas._util as _util

    return _util.print_tree_impl(structure, hide_empty_nodes)


def print_metadata_tree(
    structure: Union[IDSMetadata, IDSBase], maxdepth: int = 2
) -> None:
    """Print a tree of IDS metadata.

    This can be used to inspect which child nodes the Data Dictionary allows for the
    provided structure.

    Args:
        structure: IDS (structure) node or metadata belonging to an IDS node.
        maxdepth: Control how deep to descend into the metadata tree. When set to 0, all
            descendants are printed (caution: this can give a lot of output).

    Examples:
        .. code-block:: python

            core_profiles = imas.IDSFactory().core_profiles()
            # Print tree of the core_profiles IDS
            imas.util.print_metadata_tree(core_profiles)
            # Print descendants of the profiles_1d array of structure only:
            imas.util.print_metadata_tree(core_profiles.metadata["profiles_1d"])
            # Print descendants of the profiles_1d/electrons structure only:
            electrons_metadata = core_profiles.metadata["profiles_1d/electrons"]
            imas.util.print_metadata_tree(electrons_metadata)
    """
    import imas._util as _util

    return _util.print_metadata_tree_impl(structure, maxdepth)


def inspect(ids_node, hide_empty_nodes=False):
    """Inspect and print an IDS node.

    Inspired by `rich.inspect`, but customized for IDS specifics.
    """
    import imas._util as _util

    return _util.inspect_impl(ids_node, hide_empty_nodes)


def find_paths(node: IDSBase, query: str) -> List[str]:
    """Find all paths in the provided DD node (including children) that match the query.

    Matching is checked with :external:py:func:`re.search`.

    Args:
        node: An IDS node (e.g. an IDS or sub-structure) to search in.
        query: Regular Expression. See the Python doumentation for :external:py:mod:`re`
            for more details.

    Returns:
        A list of matching paths.

    Example:
        >>> factory = imas.IDSFactory()
        >>> core_profiles = factory.new("core_profiles")
        >>> imas.util.find_paths(core_profiles, "(^|/)time$")
        ['profiles_1d/time', 'profiles_2d/time', 'time']
    """
    dd_element = node.metadata._structure_xml
    pattern = re.compile(query)
    matching_paths = []

    for element in dd_element.iter():
        path = element.get("path", "")
        if pattern.search(path) is not None:
            matching_paths.append(path)

    return matching_paths


def calc_hash(node: IDSBase) -> bytes:
    """Calculate the hash of the provided IDS object.

    Hashes are calculated as follows:

    1.  Data nodes:

        a.  ``STR_0D``: hash of value (encoded as UTF-8)
        b.  ``STR_1D``: hash of concatenation of

            -   Length of the STR_1D (64-bit little-endian integer)
            -   hash of value[0] (encoded as UTF-8)
            -   hash of value[1] (encoded as UTF-8)
            -   ...

        c.  ``INT_0D``: hash of value (32-bit little-endian signed integer)
        d.  ``FLT_0D``: hash of value (64-bit IEEE 754 floating point number)
        e.  ``CPX_0D``: hash of value (128-bit: real, imag)
        f.  ``ND`` arrays: hash of concatenation of

            -   Dimension (8-bit integer)
            -   Shape (dimension * 64-bits little-endian integer)
            -   Concatenated data (little-endian, **Fortran memory layout**)

    2.  Array of structures nodes: hash of concatenation of

        -   Length of the AoS (64-bit little-endian integer)
        -   Hash of structure[0]
        -   Hash of structure[1]
        -   ...

    3.  Structure nodes:

        a.  Sort all children alphabetically
        b.  Remove empty children. Children are empty when:

            -   ``INT_0D``: equal to ``EMPTY_INT``
            -   ``FLT_0D``: equal to ``EMPTY_FLOAT``
            -   ``CPX_0D``: equal to ``EMPTY_COMPLEX``
            -   ``ND`` arrays: array is empty
            -   ``STR_0D``: equal to ``""``
            -   ``STR_1D``: length is 0
            -   Array of structures: length is 0
            -   Structure: all children are empty

        c.  Remove ``ids_properties/version_put`` structure
        d.  Calculate hash of concatenation of

            -   Name of child[0] (encoded as UTF-8)
            -   Hash of child[0]
            -   ...

    The hash function used is ``xxhash.xxh3_64`` from the ``xxhash`` package.

    Example:
        .. code-block:: python

            cp = imas.IDSFactory().core_profiles()
            cp.ids_properties.homogeneous_time = 0

            print(imas.util.calc_hash(cp).hex())  # 3b9b929756a242fd
    """
    return node._xxhash()


def get_parent(node: IDSBase) -> Optional[IDSBase]:
    """Get the parent of any IDS node.

    Args:
        node: Any node (structure, array of structures, data node) of an IDS.

    Returns:
        The parent node of the provided node, or None if the node is an IDS toplevel.

    Example:
        .. code-block:: python

            >>> cp = imas.IDSFactory().core_profiles()
            >>> cp.profiles_1d.resize(2)
            >>> imas.util.get_parent(cp.profiles_1d[0].electrons.temperature)
            <IDSStructure (IDS:core_profiles, profiles_1d[0]/electrons)>
            >>> imas.util.get_parent(cp.profiles_1d[0].electrons)
            <IDSStructure (IDS:core_profiles, profiles_1d[0])>
            >>> imas.util.get_parent(cp.profiles_1d[0])
            <IDSStructArray (IDS:core_profiles, profiles_1d with 2 items)>
            >>> imas.util.get_parent(cp.profiles_1d)
            <IDSToplevel (IDS:core_profiles)>
            >>> imas.util.get_parent(cp)
            >>>
    """
    if isinstance(node, IDSToplevel):
        return None
    return node._parent


def get_time_mode(node: IDSBase) -> IDSInt0D:
    """Retrieve ``ids_properties/homogeneous_time`` for any node in the IDS.

    Args:
        node: Any node (structure, array of structures, data node) of an IDS.

    Returns:
        ``ids_properties/homogeneous_time``.

    Example:
        .. code-block:: python

            >>> cp = imas.IDSFactory().core_profiles()
            >>> cp.ids_properties.homogeneous_time = 0
            >>> cp.profiles_1d.resize(2)
            >>> imas.util.get_time_mode(cp.profiles_1d[0].electrons.temperature)
            <IDSInt0D (IDS:core_profiles, ids_properties/homogeneous_time, INT_0D)>
            int(0)
    """
    return node._time_mode


def get_toplevel(node: IDSBase) -> IDSToplevel:
    """Retrieve the toplevel IDS object for any node in the IDS.

    Args:
        node: Any node (structure, array of structures, data node) of an IDS.

    Returns:
        The toplevel IDS object.

    Example:
        .. code-block:: python

            >>> cp = imas.IDSFactory().core_profiles()
            >>> cp.profiles_1d.resize(2)
            >>> imas.util.get_toplevel(cp.profiles_1d[0].electrons.temperature)
            <IDSToplevel (IDS:core_profiles)>
    """
    return node._toplevel


def is_lazy_loaded(node: IDSBase) -> bool:
    """Find out if the provided (node of an) IDS is lazy loaded.

    Args:
        node: Any node (structure, array of structures, data node) of an IDS.
    """
    return node._lazy


def get_full_path(node: IDSBase) -> str:
    """Get the full path (relative to the IDS toplevel) of the provided node.

    Caution:
        Determining the path is relatively expensive in large, nested Arrays of
        Structures: the calculation of the index suffix is O(N) in the size of the AoS.

        Using this function may result in a performance bottleneck for your application.

    Example:
        .. code-block:: python

            >>> cp = imas.IDSFactory().core_profiles()
            >>> cp.profiles_1d.resize(2)
            >>> imas.util.get_full_path(cp.profiles_1d[1].electrons.temperature)
            'profiles_1d[1]/electrons/temperature'
    """
    return node._path


def get_data_dictionary_version(obj: Union[IDSBase, DBEntry, IDSFactory]) -> str:
    """Find out the version of the data dictionary definitions that this object uses.

    Args:
        obj: Any imas-python object that is data-dictionary dependent.

    Returns:
        The data dictionary version, e.g. ``"3.38.1"``.
    """
    if isinstance(obj, (DBEntry, IDSFactory)):
        return obj.dd_version
    if isinstance(obj, IDSBase):
        return obj._version
    raise TypeError(f"Cannot get data dictionary version of '{type(obj)}'")
