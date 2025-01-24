# A minimal testcase loading an IDS file and checking that the structure built is ok
import pytest

from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT, MDSPLUS_BACKEND, MEMORY_BACKEND
from imas.test.test_helpers import open_dbentry


def test_minimal_struct_array_maxoccur(
    backend, ids_minimal_struct_array, worker_id, tmp_path
):
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_struct_array
    )
    minimal_struct_array = dbentry.factory.new("minimal_struct_array")
    minimal_struct_array.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    # maxoccur is 2, so this should raise an exception with the MDS+ backend
    minimal_struct_array.struct_array.resize(3)

    if backend == MDSPLUS_BACKEND:
        with pytest.raises(RuntimeError):
            dbentry.put(minimal_struct_array)
    else:
        dbentry.put(minimal_struct_array)

    dbentry.close()


def test_minimal_struct_array_io(
    backend, ids_minimal_struct_array, worker_id, tmp_path
):
    """Write and then read again a number on our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_struct_array
    )
    minimal_struct_array = dbentry.factory.new("minimal_struct_array")
    a = minimal_struct_array.struct_array
    minimal_struct_array.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    a.append(a._element_structure)

    # TODO: these are nested one too deeply in my opinion.
    # (a struct array contains an array of structures directly,
    #  without the intermediate one?)
    a[0].a.flt_0d = 2.0
    a.append(a._element_structure)
    a[1].a.flt_0d = 4.0

    dbentry.put(minimal_struct_array)
    assert a[0].a.flt_0d.value == 2.0
    assert a[1].a.flt_0d.value == 4.0

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_struct_array
    )
    minimal_struct_array2 = dbentry2.get("minimal_struct_array")
    assert minimal_struct_array2.struct_array[0].a.flt_0d.value == 2.0
    assert minimal_struct_array2.struct_array[1].a.flt_0d.value == 4.0

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()
