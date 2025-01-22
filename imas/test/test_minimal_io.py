# A minimal testcase loading an IDS file and checking that the structure built is ok
from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT, MEMORY_BACKEND
from imas.test.test_helpers import open_dbentry


def test_minimal_io(backend, ids_minimal, worker_id, tmp_path):
    """Write and then read again a number on our minimal IDS."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, xml_path=ids_minimal)
    minimal = dbentry.factory.new("minimal")
    minimal.a = 2.0
    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)
    assert minimal.a.value == 2.0

    dbentry2 = open_dbentry(backend, "a", worker_id, tmp_path, xml_path=ids_minimal)
    minimal2 = dbentry2.get("minimal")
    assert minimal2.a.value == 2.0

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()
