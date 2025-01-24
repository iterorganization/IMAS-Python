"""A minimal testcase loading an IDS file and checking that the structure built is ok
"""

import numpy as np

from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT, MEMORY_BACKEND
from imas.ids_factory import IDSFactory
from imas.test.test_helpers import fill_with_random_data, open_dbentry
from imas.test.test_minimal_types_io import TEST_DATA


def test_minimal_types_str_1d_decode(ids_minimal_types):
    minimal = IDSFactory(xml_path=ids_minimal_types).new("minimal")
    minimal.str_1d = [b"test", b"test2"]
    assert minimal.str_1d.value == ["test", "test2"]


def test_minimal_types_str_1d_decode_and_put(
    backend, ids_minimal_types, worker_id, tmp_path
):
    """The access layer changed 1d string types to bytes.
    This is unexpected, especially since on read it is converted from bytes to string
    again (which implies that the proper form for in python is as strings)"""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    minimal.str_1d = [b"test", b"test2"]
    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT

    assert minimal.str_1d.value == ["test", "test2"]
    dbentry.put(minimal)
    assert minimal.str_1d.value == ["test", "test2"]
    dbentry.close()


def test_minimal_types_io_automatic(backend, ids_minimal_types, worker_id, tmp_path):
    """Write and then read again our minimal IDS."""
    dbentry = open_dbentry(
        backend, "w", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal = dbentry.factory.new("minimal")
    fill_with_random_data(minimal)

    minimal.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    dbentry.put(minimal)

    dbentry2 = open_dbentry(
        backend, "a", worker_id, tmp_path, xml_path=ids_minimal_types
    )
    minimal2 = dbentry2.get("minimal")
    for k, v in TEST_DATA.items():
        if isinstance(v, np.ndarray):
            assert np.array_equal(minimal2[k].value, minimal[k].value)
        else:
            if isinstance(minimal2[k].value, np.ndarray):
                assert np.array_equal(
                    minimal2[k].value,
                    np.asarray(minimal[k].value, dtype=minimal2[k].value.dtype),
                )
            else:
                assert minimal2[k].value == minimal[k].value

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()
