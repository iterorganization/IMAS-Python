import pytest

from imas.db_entry import DBEntry
from imas.exception import DataEntryException
from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT
from imas.ids_factory import IDSFactory


def test_readwrite(tmp_path):
    fname = tmp_path / "test-rw.nc"
    ids = IDSFactory().core_profiles()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT

    with pytest.raises(FileNotFoundError):
        DBEntry(fname, "r")  # File does not exist
    with DBEntry(fname, "x") as entry:
        entry.put(ids)
    with DBEntry(fname, "w") as entry:
        with pytest.raises(DataEntryException):
            entry.get("core_profiles")  # File overwritten, IDS does not exist
        entry.put(ids)
    with pytest.raises(OSError):
        DBEntry(fname, "x")  # file already exists
    with DBEntry(fname, "a") as entry:
        with pytest.raises(RuntimeError):  # FIXME: change error class
            entry.put(ids)  # Cannot overwrite existing IDS
        # But we can write a new occurrence
        entry.put(ids, 1)
