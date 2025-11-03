import numpy as np
import pytest

import imas
import imas.training
from imas.util import to_xarray

pytest.importorskip("xarray")


@pytest.fixture
def entry(requires_imas, monkeypatch):
    monkeypatch.setenv("IMAS_VERSION", "3.39.0")  # Use fixed DD version
    return imas.training.get_training_db_entry()


def test_to_xarray_invalid_argtype():
    ids = imas.IDSFactory("3.39.0").core_profiles()

    with pytest.raises(TypeError):
        to_xarray("test")
    with pytest.raises(TypeError):
        to_xarray(ids.time)
    with pytest.raises(TypeError):
        to_xarray(ids.ids_properties)


def test_to_xarray_invalid_paths():
    ids = imas.IDSFactory("3.39.0").core_profiles()

    with pytest.raises(ValueError, match="xyz"):
        to_xarray(ids, "xyz")
    with pytest.raises(ValueError, match="ids_properties/xyz"):
        to_xarray(ids, "ids_properties/xyz")
    with pytest.raises(ValueError, match="Xtime"):
        to_xarray(ids, "time", "Xtime")


def validate_trainingdb_electron_temperature_dataset(ds):
    assert ds.sizes == {"time": 3, "profiles_1d.grid.rho_tor_norm:i": 101}
    assert ds.data_vars.keys() == {"profiles_1d.electrons.temperature"}
    assert ds.coords.keys() == {"time", "profiles_1d.grid.rho_tor_norm"}

    # Check that values are loaded as expected
    assert np.allclose(ds["time"], [3.987222, 432.937598, 792.0])
    assert np.allclose(
        ds.isel(time=1)["profiles_1d.electrons.temperature"][10:13],
        [17728.81703089, 17440.78020568, 17139.35431082],
    )


def test_to_xarray_lazy_loaded(entry):
    ids = entry.get("core_profiles", lazy=True)

    with pytest.raises(RuntimeError):
        to_xarray(ids)

    ds = to_xarray(ids, "profiles_1d.electrons.temperature")
    validate_trainingdb_electron_temperature_dataset(ds)


def test_to_xarray_from_trainingdb(entry):
    ids = entry.get("core_profiles")

    ds = to_xarray(ids)
    validate_trainingdb_electron_temperature_dataset(
        ds["profiles_1d.electrons.temperature"].to_dataset()
    )
    ds = to_xarray(ids, "profiles_1d.electrons.temperature")
    validate_trainingdb_electron_temperature_dataset(ds)

    ds = to_xarray(
        ids, "profiles_1d.electrons.temperature", "profiles_1d/electrons/density"
    )
    assert ds.data_vars.keys() == {
        "profiles_1d.electrons.temperature",
        "profiles_1d.electrons.density",
    }


def test_to_xarray():
    ids = imas.IDSFactory("3.39.0").core_profiles()

    ids.profiles_1d.resize(2)
    ids.profiles_1d[0].electrons.temperature = [1.0, 2.0]
    ids.profiles_1d[0].grid.rho_tor_norm = [0.0, 1.0]
    ids.profiles_1d[0].time = 0.0

    # These should all be identical:
    ds1 = to_xarray(ids)
    ds2 = to_xarray(ids, "profiles_1d.electrons.temperature")
    ds3 = to_xarray(ids, "profiles_1d/electrons/temperature")
    assert ds1.equals(ds2)
    assert ds2.equals(ds3)
