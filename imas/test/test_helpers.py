import logging
import random
import string

import numpy as np
import pytest
from packaging.version import Version

from imas.db_entry import DBEntry
from imas.ids_data_type import IDSDataType
from imas.ids_defs import (
    ASCII_BACKEND,
    IDS_TIME_MODE_HETEROGENEOUS,
    IDS_TIME_MODE_HOMOGENEOUS,
    IDS_TIME_MODE_INDEPENDENT,
)
from imas.ids_metadata import IDSType
from imas.ids_primitive import IDSPrimitive, IDSString1D
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure
from imas.ids_toplevel import IDSToplevel
from imas.util import idsdiffgen, visit_children

logger = logging.getLogger(__name__)

BASE_STRING = string.ascii_uppercase + string.digits


def randdims(ndims):
    """Return a list of n random numbers representing
    the shapes in n dimensions"""
    return random.sample(range(1, 7), ndims)


def random_string():
    return "".join(random.choices(BASE_STRING, k=random.randint(0, 128)))


def random_data(ids_type, ndims):
    if ids_type is IDSDataType.STR:
        if ndims == 0:
            return random_string()
        elif ndims == 1:
            return [random_string() for _ in range(random.randint(0, 3))]
        else:
            raise NotImplementedError(
                "Strings of dimension 2 or higher are not supported"
            )
    elif ids_type is IDSDataType.INT:
        return np.random.randint(0, 2**31 - 1, size=randdims(ndims), dtype=np.int32)
    elif ids_type is IDSDataType.FLT:
        return np.random.random_sample(size=randdims(ndims))
    elif ids_type is IDSDataType.CPX:
        size = randdims(ndims)
        return np.random.random_sample(size) + 1j * np.random.random_sample(size)
    else:
        raise ValueError("Unknown data type %s requested to fill", ids_type)


def fill_with_random_data(structure, max_children=3):
    """Fill a structure with random data.

    Sets homogeneous_time to homogeneous _always_.
    TODO: also test other time types

    Args:
        structure: IDS object to fill
        max_children: The maximum amount of children to create for IDSStructArrays.
    """
    is_toplevel = isinstance(structure, IDSToplevel)
    for child_name in structure._children:
        if not is_toplevel and child_name == "time":
            continue  # skip non-root time arrays when in HOMOGENEOUS_TIME
        child = structure[child_name]

        if isinstance(child, IDSStructure):
            fill_with_random_data(child, max_children)
        elif isinstance(child, IDSStructArray):
            n_children = min(child.metadata.maxoccur or max_children, max_children)
            child.resize(n_children)
            # choose which child will get the max number of grand-children
            max_child = random.randrange(n_children)
            for i, ch in enumerate(child.value):
                max_grand_children = max_children if i == max_child else 1
                fill_with_random_data(ch, max_grand_children)
            # Delete empty structures at the back
            while len(child) > 0 and not child[-1].has_value:
                child.resize(len(child) - 1, keep=True)
        else:  # leaf node
            if child_name == "homogeneous_time":
                child.value = IDS_TIME_MODE_HOMOGENEOUS
            else:
                child.value = random_data(child.metadata.data_type, child.metadata.ndim)


def maybe_set_random_value(primitive: IDSPrimitive, leave_empty: float) -> None:
    """Set the value of an IDS primitive with a certain chance.

    If the IDSPrimitive has coordinates, then the size of the coordinates is taken into
    account as well.

    Args:
        primitive: IDSPrimitive to set the value of
        leave_empty: Chance that this primitive remains empty.
    """
    # Skip obsolescent nodes
    if getattr(primitive.metadata, "lifecycle_status", None) == "obsolescent":
        return

    if random.random() < leave_empty:
        return

    ndim = primitive.metadata.ndim
    if ndim == 0:
        primitive.value = random_data(primitive.metadata.data_type, ndim)
        return

    shape = []
    for dim, coordinate in enumerate(primitive.metadata.coordinates):
        same_as = primitive.metadata.coordinates_same_as[dim]
        if not coordinate.has_validation and not same_as.has_validation:
            if primitive.metadata.name.endswith("_error_upper"):
                # <name>_error_upper should only be filled when <name> is
                name = primitive.metadata.name[: -len("_error_upper")]
                data = primitive._parent[name]
                if not data.has_value:
                    return
                size = data.shape[dim]
            elif primitive.metadata.name.endswith("_error_lower"):
                # <name>_error_lower should only be filled when <name>_error_upper is
                name = primitive.metadata.name[: -len("_error_lower")] + "_error_upper"
                data = primitive._parent[name]
                if not data.has_value:
                    return
                size = data.shape[dim]
            else:
                # we can independently choose a size for this dimension:
                size = random.randint(1, 6)
        elif coordinate.references or same_as.references:
            try:
                if coordinate.references:
                    refs = [ref.goto(primitive) for ref in coordinate.references]
                    filled_refs = [ref for ref in refs if len(ref) > 0]
                    assert len(filled_refs) in (0, 1)
                    coordinate_element = filled_refs[0] if filled_refs else refs[0]
                else:
                    coordinate_element = same_as.references[0].goto(primitive)
            except (ValueError, AttributeError):
                # Ignore invalid coordinate specs
                coordinate_element = np.ones((1,) * 6)

            if len(coordinate_element) == 0:
                # Scale chance of not setting a coordinate by our number of dimensions,
                # such that overall there is roughly a 50% chance that any coordinate
                # remains empty
                maybe_set_random_value(coordinate_element, 0.5**ndim)
            size = coordinate_element.shape[0 if coordinate.references else dim]

            if coordinate.size:  # coordinateX = <path> OR 1...1
                # Coin flip whether to use the size as determined by
                # coordinate.references, or the size from coordinate.size
                if random.random() < 0.5:
                    size = coordinate.size
        else:
            size = coordinate.size
        if size == 0:
            return  # Leave empty
        shape.append(size)

    if primitive.metadata.data_type is IDSDataType.STR:
        primitive.value = [random_string() for i in range(shape[0])]
    elif primitive.metadata.data_type is IDSDataType.INT:
        primitive.value = np.random.randint(
            -(2**31), 2**31 - 1, size=shape, dtype=np.int32
        )
    elif primitive.metadata.data_type is IDSDataType.FLT:
        primitive.value = np.random.random_sample(size=shape)
    elif primitive.metadata.data_type is IDSDataType.CPX:
        val = np.random.random_sample(shape) + 1j * np.random.random_sample(shape)
        primitive.value = val
    else:
        raise ValueError(f"Invalid IDS data type: {primitive.metadata.data_type}")


def fill_consistent(structure: IDSStructure, leave_empty: float = 0.2):
    """Fill a structure with random data, such that coordinate sizes are consistent.

    Sets homogeneous_time to heterogeneous (always).

    Args:
        structure: IDSStructure object to (recursively fill)
        leave_empty: factor (0-1) of nodes to leave empty

    Returns:
        Nothing: if the provided IDSStructue is an IDSToplevel
        exclusive_coordinates: list of IDSPrimitives that have exclusive alternative
            coordinates. These are initially not filled, and only at the very end of
            filling an IDSToplevel, a choice is made between the exclusive coordinates.
    """
    if isinstance(structure, IDSToplevel):
        unsupported_ids_name = (
            "amns_data"
            if Version(structure._version) < Version("3.42.0")
            else "thomson_scattering"
        )
        if structure.metadata.name == unsupported_ids_name:
            pytest.skip(
                f"fill_consistent doesn't support IDS {structure.metadata.name} "
                f"for Data Dictionary version {structure._version}."
            )

        time_mode = IDS_TIME_MODE_HETEROGENEOUS
        if structure.metadata.type is IDSType.CONSTANT:
            time_mode = IDS_TIME_MODE_INDEPENDENT
        structure.ids_properties.homogeneous_time = time_mode

    exclusive_coordinates = []

    for child in structure:
        if isinstance(child, IDSStructure):
            exclusive_coordinates.extend(fill_consistent(child, leave_empty))

        elif isinstance(child, IDSStructArray):
            if child.metadata.coordinates[0].references:
                try:
                    coor = child.coordinates[0]
                except RuntimeError:  # Ignore failed coordinate retrieval
                    coor = []
                if len(coor) == 0:
                    if isinstance(coor, IDSPrimitive):
                        # maybe fill with random data:
                        try:
                            maybe_set_random_value(coor, leave_empty)
                        except (RuntimeError, ValueError):
                            pass
                        child.resize(len(coor))
                    else:  # a numpy array is returned, resize to coordinate size or 1
                        child.resize(child.metadata.coordinates[0].size or 1)
                        if child.metadata.type.is_dynamic:
                            # This is a dynamic AoS with time coordinate inside: we must
                            # set the time coordinate to something else than EMPTY_FLOAT
                            # to pass validation:
                            child[0].time = 0.0
            else:
                child.resize(child.metadata.coordinates[0].size or 1)
            for ele in child:
                exclusive_coordinates.extend(fill_consistent(ele, leave_empty))

        else:  # IDSPrimitive
            coordinates = child.metadata.coordinates
            if child.metadata.path_string == "ids_properties/homogeneous_time":
                pass  # We already set homogeneous_time
            elif child.has_value:
                pass  # Already encountered somewhere
            elif any(len(coordinate.references) > 1 for coordinate in coordinates):
                exclusive_coordinates.append(child)
            else:
                try:
                    maybe_set_random_value(child, leave_empty)
                except (RuntimeError, ValueError):
                    pass

    if isinstance(structure, IDSToplevel):
        # handle exclusive_coordinates
        for element in exclusive_coordinates:
            for dim, coordinate in enumerate(element.metadata.coordinates):
                try:
                    refs = [ref.goto(element) for ref in coordinate.references]
                except RuntimeError:
                    break  # Ignore paths that cannot be resolved
                filled_refs = [ref for ref in refs if len(ref) > 0]
                if len(filled_refs) == 0:
                    continue

                # Unset conflicting coordinates
                while len(filled_refs) > 1:
                    random.shuffle(filled_refs)
                    coor = filled_refs.pop()
                    unset_coordinate(coor)

            maybe_set_random_value(element, leave_empty)
    else:
        return exclusive_coordinates


def unset_coordinate(coordinate):
    # Unset the coordinate quantity
    coordinate.value = []
    # Find all elements that also have this as a coordinate and unset...
    parent = coordinate._dd_parent
    while parent.metadata.data_type is not IDSDataType.STRUCT_ARRAY:
        parent = parent._dd_parent

    def callback(element):
        if hasattr(element, "coordinates") and element.has_value:
            for ele_coor in element.coordinates:
                if ele_coor is coordinate:
                    element.value = []
                    return

    visit_children(callback, parent)


def compare_children(st1, st2, deleted_paths=set(), accept_lazy=False):
    """Perform a deep compare of two structures using asserts.

    All paths in ``deleted_paths`` are asserted that they are deleted in st2.
    """
    for description, node1, node2 in idsdiffgen(st1, st2, accept_lazy=accept_lazy):
        if node1 is not None:
            # Check if this is a deleted path
            path = node1.metadata.path_string
            # No duplicate entries for _error_upper, _error_lower and _error_index
            path = path.partition("_error_")[0]
            if path in deleted_paths:
                assert node2 is None
                continue
        # Workaround for https://jira.iter.org/browse/IMAS-4948:
        if isinstance(node1, IDSString1D) or isinstance(node2, IDSString1D):
            assert (
                node1 == node2
                or (node1 == [""] and not node2)
                or (node2 == [""] and not node1)
            )
            continue
        # Not a deleted path
        assert False, ("Unequal nodes", node1, node2)


def open_dbentry(
    backend, mode, worker_id, tmp_path, dd_version=None, xml_path=None
) -> DBEntry:
    """Open a DBEntry, with a tmpdir in place of the user argument"""
    if worker_id == "master":
        pulse = 1
    else:
        pulse = int(worker_id[2:]) + 1

    dbentry = DBEntry(
        backend,
        "test",
        pulse,
        0,
        str(tmp_path),
        dd_version=dd_version,
        xml_path=xml_path,
    )
    options = f"-prefix {tmp_path}/" if backend == ASCII_BACKEND else None
    if mode == "w":
        dbentry.create(options=options)
    else:
        dbentry.open(options=options)

    return dbentry
