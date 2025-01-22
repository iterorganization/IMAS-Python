"""A minimal testcase loading an IDS file and checking that the structure built is ok"""

import numpy as np

from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT, MEMORY_BACKEND
from imas.test.test_helpers import open_dbentry, randdims

TEST_DATA = {
    "str_0d": "test",
    "str_1d": ["test0", "test1"],
    "str_type": "test_legacy",
    "str_1d_type": ["test0_legacy", "test1_legacy"],
    "flt_type": 2.0,
    "flt_1d_type": np.asarray([3.0, 4.0]),
    "int_type": 5,
}
for i in range(0, 7):
    # dimensions are random
    TEST_DATA["flt_%dd" % i] = np.random.random_sample(size=randdims(i))
    if i < 4:
        TEST_DATA["int_%dd" % i] = np.random.randint(0, 1000, size=randdims(i))


def test_minimal_types_io(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again a number on our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    for k, v in TEST_DATA.items():
        minimal[k] = v

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    for k, v in TEST_DATA.items():
        if isinstance(v, np.ndarray):
            assert np.array_equal(minimal2[k].value, v)
        else:
            assert minimal2[k].value == v

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_large_numbers(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again a large number"""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    minimal["int_0d"] = 955683416

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    assert minimal2["int_0d"] == 955683416

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()
