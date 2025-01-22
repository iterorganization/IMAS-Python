import pytest
from packaging.version import Version

import imas
from imas.backends.imas_core.imas_interface import ll_interface
from imas.test.test_helpers import open_dbentry


@pytest.fixture
def filled_dbentry(backend, worker_id, tmp_path):
    if backend == imas.ids_defs.MEMORY_BACKEND:
        pytest.skip("list_occurrences is not implemented for the MEMORY backend")
    entry = open_dbentry(backend, "w", worker_id, tmp_path)

    for i in range(3):
        cp = entry.factory.core_profiles()
        cp.ids_properties.homogeneous_time = 0
        cp.ids_properties.comment = f"core_profiles occurrence {i}"
        entry.put(cp, i)

    for i in [0, 1, 3, 6]:
        mag = entry.factory.core_sources()
        mag.ids_properties.homogeneous_time = 0
        mag.ids_properties.comment = f"core_sources occurrence {i}"
        entry.put(mag, i)

    yield entry
    entry.close()


def test_list_occurrences_no_path(filled_dbentry):
    if ll_interface._al_version >= Version("5.1"):
        occurrences = filled_dbentry.list_all_occurrences("core_profiles")
        assert occurrences == [0, 1, 2]

        occurrences = filled_dbentry.list_all_occurrences("core_sources")
        assert occurrences == [0, 1, 3, 6]

        assert filled_dbentry.list_all_occurrences("magnetics") == []

    else:  # AL 5.0 or lower
        with pytest.raises(RuntimeError):
            filled_dbentry.list_all_occurrences("core_profiles")
        with pytest.raises(RuntimeError):
            filled_dbentry.list_all_occurrences("core_sources")
        with pytest.raises(RuntimeError):
            filled_dbentry.list_all_occurrences("magnetics")


def test_list_occurrences_with_path(backend, filled_dbentry):
    if backend == imas.ids_defs.ASCII_BACKEND:
        pytest.skip("Lazy loading is not supported by the ASCII backend")

    comment = "ids_properties/comment"
    if ll_interface._al_version >= Version("5.1"):
        res = filled_dbentry.list_all_occurrences("core_profiles", comment)
        assert res[0] == [0, 1, 2]
        assert res[1] == [
            "core_profiles occurrence 0",
            "core_profiles occurrence 1",
            "core_profiles occurrence 2",
        ]

        res = filled_dbentry.list_all_occurrences("core_sources", comment)
        assert res[0] == [0, 1, 3, 6]
        assert res[1] == [
            "core_sources occurrence 0",
            "core_sources occurrence 1",
            "core_sources occurrence 3",
            "core_sources occurrence 6",
        ]

        res = filled_dbentry.list_all_occurrences("magnetics", comment)
        assert res == ([], [])

    else:  # AL 5.0 or lower
        with pytest.raises(RuntimeError):
            filled_dbentry.list_all_occurrences("core_profiles", comment)
        with pytest.raises(RuntimeError):
            filled_dbentry.list_all_occurrences("core_sources", comment)
        with pytest.raises(RuntimeError):
            filled_dbentry.list_all_occurrences("magnetics", comment)
