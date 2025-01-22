import pytest

import imas
import imas.ids_defs
from imas.backends.imas_core.imas_interface import has_imas, ll_interface
from imas.exception import UnknownDDVersion
from imas.test.test_helpers import compare_children, open_dbentry


def test_dbentry_contextmanager(requires_imas):
    entry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "test", 1, 1)
    entry.create()
    ids = entry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = 0
    ids.ids_properties.comment = "test context manager"
    entry.put(ids)

    with imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "test", 1, 1) as entry2:
        ids2 = entry2.get("core_profiles")
        assert ids2.ids_properties.comment == ids.ids_properties.comment

    # Check that entry2 was closed
    assert entry2._dbe_impl is None


@pytest.mark.skipif(
    not has_imas or ll_interface._al_version.major < 5,
    reason="URI API not available",
)
def test_dbentry_contextmanager_uri(tmp_path):
    entry = imas.DBEntry(f"imas:ascii?path={tmp_path}/testdb", "w")
    ids = entry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = 0
    ids.ids_properties.comment = "test context manager"
    entry.put(ids)

    with imas.DBEntry(f"imas:ascii?path={tmp_path}/testdb", "r") as entry2:
        ids2 = entry2.get("core_profiles")
        assert ids2.ids_properties.comment == ids.ids_properties.comment

    # Check that entry2 was closed
    assert entry2._dbe_impl is None


def get_entry_attrs(entry: imas.DBEntry):
    return (
        entry.backend_id,
        entry.db_name,
        entry.pulse,
        entry.run,
        entry.user_name,
        entry.data_version,
    )


def test_dbentry_constructor():
    with pytest.raises(TypeError):
        imas.DBEntry()  # no arguments
    with pytest.raises(TypeError):
        imas.DBEntry(1)  # not enough arguments
    with pytest.raises(TypeError):
        imas.DBEntry(1, 2, 3)  # not enough arguments
    with pytest.raises(TypeError):
        imas.DBEntry(1, 2, 3, 4, 5, 6, 7)  # too many arguments
    with pytest.raises(TypeError):
        imas.DBEntry("test", uri="test")  # Double URI argument
    with pytest.raises(TypeError):
        imas.DBEntry(1, 2, 3, 4, shot=5)  # Multiple values for argument pulse
    with pytest.raises(ValueError):
        imas.DBEntry(1, 2, pulse=3, run=4, shot=5)  # Both shot and pulse

    entry = imas.DBEntry(1, 2, 3, 4)
    assert get_entry_attrs(entry) == (1, 2, 3, 4, None, None)
    entry = imas.DBEntry(backend_id=1, db_name=2, pulse=3, run=4)
    assert get_entry_attrs(entry) == (1, 2, 3, 4, None, None)
    # Shot behaves as alias of pulse
    entry = imas.DBEntry(backend_id=1, db_name=2, shot=3, run=4)
    assert get_entry_attrs(entry) == (1, 2, 3, 4, None, None)
    entry = imas.DBEntry(1, 2, 3, 4, 5, 6)
    assert get_entry_attrs(entry) == (1, 2, 3, 4, 5, 6)
    entry = imas.DBEntry(1, 2, 3, 4, data_version=6)
    assert get_entry_attrs(entry) == (1, 2, 3, 4, None, 6)


def test_ignore_unknown_dd_version(monkeypatch, worker_id, tmp_path):
    entry = open_dbentry(imas.ids_defs.MEMORY_BACKEND, "w", worker_id, tmp_path)
    ids = entry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = 0
    ids.ids_properties.comment = "Test unknown DD version"
    # Put this IDS with an invalid DD version
    with monkeypatch.context() as m:
        m.setattr(entry.factory, "_version", "invalid DD version")
        assert entry.dd_version == "invalid DD version"
        entry.put(ids)

    with pytest.raises(UnknownDDVersion) as exc_info:
        entry.get("core_profiles")
    assert "ignore_unknown_dd_version" in str(exc_info.value)
    ids2 = entry.get("core_profiles", ignore_unknown_dd_version=True)
    assert ids2.ids_properties.version_put.data_dictionary == "invalid DD version"
    compare_children(ids, ids2)
    # Test that autoconvert plays nicely with this option as well
    ids3 = entry.get("core_profiles", ignore_unknown_dd_version=True, autoconvert=False)
    compare_children(ids, ids3)
