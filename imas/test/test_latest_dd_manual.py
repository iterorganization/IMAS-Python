"""A testcase checking if writing and then reading works for the latest full
data dictionary version.
"""

from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS, MEMORY_BACKEND
from imas.ids_factory import IDSFactory
from imas.test.test_helpers import open_dbentry


def test_latest_dd_manual(backend, worker_id, tmp_path):
    """Write and then read again a single IDSToplevel."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    ids_name = "pulse_schedule"
    ids = IDSFactory().new(ids_name)
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.ids_properties.comment = "test"

    assert ids.ids_properties.comment.value == "test"

    dbentry.put(ids)

    dbentry2 = open_dbentry(backend, "a", worker_id, tmp_path)
    ids2 = dbentry2.get(ids_name)
    assert ids2.ids_properties.comment.value == "test"

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_dir():
    """Test calling `dir()` on `IDSFactory` to test if we can see IDSes"""
    factory = IDSFactory()
    f_dir = dir(factory)
    # Check if we can see the first and last stable IDS
    assert "amns_data" in f_dir, "Could not find amns_data in dir(IDSFactory())"
    assert "workflow" in f_dir, "Could not find workflow in dir(IDSFactory())"
    assert "__init__" in f_dir, "Could not find base attributes in dir(IDSFactory())"
