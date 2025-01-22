# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
from pathlib import PosixPath

import pytest

try:
    from importlib.resources import files
except ImportError:  # Python 3.8 support
    from importlib_resources import files

import imas.training


def test_data_exists():
    data_file: PosixPath = files(imas) / "assets/ITER_134173_106_equilibrium.ids"
    assert data_file.exists()


@pytest.fixture
def test_data(requires_imas):
    db_entry = imas.training.get_training_db_entry()
    yield db_entry
    db_entry.close()


def test_data_is_sane(test_data):
    assert isinstance(test_data, imas.DBEntry)
    eq = test_data.get("equilibrium")
    assert len(eq.time_slice) == 3
    ts = eq.time_slice[0]
    r = ts.boundary.outline.r
    z = ts.boundary.outline.z

    # Test a few relevant numbers to check if data loading went okay
    assert r.value[0] == pytest.approx(7.2896011)
    assert r.value[-1] == pytest.approx(7.29120937)
    assert z.value[0] == pytest.approx(-1.00816660e-01)
    assert z.value[-1] == pytest.approx(-9.60027185e-14)
