# A minimal testcase loading an IDS file and checking that the structure built is ok
import string

from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT, MEMORY_BACKEND
from imas.test.test_helpers import open_dbentry


def test_str_1d_empty(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again a string on our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    minimal.str_1d = []

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    assert list(minimal2.str_1d.value) == []

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_str_1d_long_single(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again a string on our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    minimal.str_1d = [string.ascii_uppercase * 100]

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    assert minimal2.str_1d.value == [string.ascii_uppercase * 100]

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_str_1d_multiple(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again a string on our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    minimal.str_1d = [string.ascii_uppercase, string.ascii_lowercase]

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    assert minimal2.str_1d.value == [
        string.ascii_uppercase,
        string.ascii_lowercase,
    ]

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_str_1d_long_multiple(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again a string on our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    minimal.str_1d = [string.ascii_uppercase * 100, string.ascii_lowercase * 100]

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    assert minimal2.str_1d.value == [
        string.ascii_uppercase * 100,
        string.ascii_lowercase * 100,
    ]

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()
