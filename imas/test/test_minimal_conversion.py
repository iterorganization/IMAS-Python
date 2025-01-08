from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT, MEMORY_BACKEND
from imas.test.test_helpers import open_dbentry


def test_minimal_io_read_flt_int(
    backend, ids_minimal, ids_minimal2, worker_id, tmp_path
):
    """Write and then read again a number on our minimal IDS."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, xml_path=ids_minimal)
    minimal = dbentry.factory.new("minimal")
    minimal.a = 2.4
    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)
    assert minimal.a.value == 2.4

    # ids_minimal2 changed a float to an int
    dbentry2 = open_dbentry(backend, "r", worker_id, tmp_path, xml_path=ids_minimal2)
    minimal2 = dbentry2.get("minimal")
    assert minimal2.a.value == 2

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_minimal_io_read_int_flt(
    backend, ids_minimal, ids_minimal2, worker_id, tmp_path
):
    """Write and then read again a number on our minimal IDS."""
    dbentry2 = open_dbentry(backend, "w", worker_id, tmp_path, xml_path=ids_minimal2)
    minimal2 = dbentry2.factory.new("minimal")
    minimal2.a = 2
    minimal2.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry2.put(minimal2)
    assert minimal2.a.value == 2

    # ids_minimal2 changed a float to an int
    dbentry = open_dbentry(backend, "r", worker_id, tmp_path, xml_path=ids_minimal)
    minimal = dbentry.get("minimal")
    assert minimal.a.value == 2.0

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()
