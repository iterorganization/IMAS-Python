import logging
from unittest.mock import Mock

import numpy as np
import pytest

from imas import DBEntry, IDSFactory
from imas.exception import ValidationError
from imas.ids_defs import (
    IDS_TIME_MODE_HETEROGENEOUS,
    IDS_TIME_MODE_HOMOGENEOUS,
    IDS_TIME_MODE_INDEPENDENT,
    MEMORY_BACKEND,
)
from imas.test.test_helpers import fill_consistent


@pytest.fixture(autouse=True)
def raise_on_logged_warnings(caplog):
    """Catch warnings logged by validate() and fail the testcase if there are any."""
    yield
    records = [
        rec for rec in caplog.get_records("call") if rec.levelno >= logging.WARNING
    ]
    if records:
        pytest.fail(f"Warning(s) encountered during test: {records}")


def test_validate_time_mode():
    cp = IDSFactory().core_profiles()
    with pytest.raises(ValidationError):
        cp.validate()

    for time_mode in [
        IDS_TIME_MODE_HOMOGENEOUS,
        IDS_TIME_MODE_HETEROGENEOUS,
        IDS_TIME_MODE_INDEPENDENT,
    ]:
        cp.ids_properties.homogeneous_time = time_mode
        cp.validate()


def test_validate_time_coordinate_homogeneous():
    cp = IDSFactory("3.39.0").core_profiles()
    cp.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    cp.time = np.array([1.0, 2.0])
    cp.profiles_1d.resize(2)
    cp.validate()

    cp.profiles_1d.resize(3)
    with pytest.raises(ValidationError):
        # non-matching size
        cp.validate()


def test_validate_time_coordinate_heterogeneous_core_profiles():
    cp = IDSFactory("3.39.0").core_profiles()
    cp.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    cp.profiles_1d.resize(2)
    with pytest.raises(ValidationError):
        cp.validate()  # Unset cp.profiles_1d.time
    cp.profiles_1d[0].time = 1.0
    with pytest.raises(ValidationError):
        cp.validate()  # Unset cp.profiles_1d.time
    cp.profiles_1d[1].time = 2.0
    cp.validate()


def test_validate_time_mode_heterogeneous_pf_active():
    pfa = IDSFactory("3.39.0").pf_active()
    pfa.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    pfa.coil.resize(1)
    pfa.coil[0].current.data = np.linspace(0, 1, 10)
    with pytest.raises(ValidationError):
        pfa.validate()
    pfa.coil[0].current.time = np.linspace(0, 1, 9)  # one too short
    with pytest.raises(ValidationError):
        pfa.validate()
    pfa.coil[0].current.time = np.linspace(0, 1, 10)
    pfa.validate()

    pfa.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    with pytest.raises(ValidationError):
        pfa.validate()
    pfa.time = np.linspace(0, 1, 10)
    pfa.validate()


def test_validate_time_mode_independent():
    cp = IDSFactory("3.39.0").core_profiles()
    cp.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    cp.validate()
    cp.profiles_1d.resize(1)
    with pytest.raises(ValidationError):
        cp.validate()


def test_fixed_size_coordinates_two():
    mag = IDSFactory("3.39.0").magnetics()
    mag.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    mag.b_field_pol_probe.resize(1)
    mag.validate()
    for bandwidth_size in [0, 1, 2, 3, 4, 1000]:
        mag.b_field_pol_probe[0].bandwidth_3db = np.linspace(0, 1, bandwidth_size)
        if bandwidth_size in (0, 2):
            mag.validate()
        else:  # coordinate1 = 1...2, so only size 0 or 2 is allowed
            with pytest.raises(ValidationError):
                mag.validate()


def test_fixed_size_coordinates_three():
    wall = IDSFactory("3.39.0").wall()
    wall.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    wall.time = np.linspace(0, 1, 10)
    wall.global_quantities.electrons.particle_flux_from_wall = np.ones((3, 10))
    wall.validate()
    for size in [1, 2, 4, 5]:
        wall.global_quantities.electrons.particle_flux_from_wall = np.ones((size, 10))
        with pytest.raises(ValidationError):
            wall.validate()


def test_validate_indirect_coordinates():
    """Test indirect coordinates like
    coordinate1=coordinate_system(process(i1)/coordinate_index)/coordinate(1)
    """
    amns = IDSFactory("3.39.0").amns_data()
    amns.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    amns.process.resize(1)
    amns.process[0].charge_state.resize(1)
    amns.process[0].charge_state[0].table_1d = np.ones(10)
    with pytest.raises(ValidationError):
        # unset amns.process[0].coordinate_index
        amns.validate()

    # create some coordinate systems
    amns.coordinate_system.resize(3)
    for i in range(3):
        amns.coordinate_system[i].coordinate.resize(6)
        for j in range(6):
            amns.coordinate_system[i].coordinate[j].label = f"label_{i}_{j}"
            values = np.linspace(0, 1, 1 + i + j)
            amns.coordinate_system[i].coordinate[j].values = values

    amns.process[0].coordinate_index = 1
    amns.process[0].charge_state[0].table_1d = np.ones(1)
    amns.validate()

    for i in range(6):
        shape = [1, 2, 3, 4, 5, 6]
        shape[i] = shape[i] + 1
        amns.process[0].charge_state[0].table_6d = np.ones(shape)
        with pytest.raises(ValidationError):
            amns.validate()
    amns.process[0].charge_state[0].table_6d = np.ones((1, 2, 3, 4, 5, 6))
    amns.validate()

    amns.process[0].coordinate_index = 3
    with pytest.raises(ValidationError):
        amns.validate()
    amns.process[0].charge_state[0].table_1d = np.ones(3)
    amns.process[0].charge_state[0].table_6d = np.ones((3, 4, 5, 6, 7, 8))
    amns.validate()


def test_validate_exclusive_references():
    distr = IDSFactory("3.39.0").distributions()
    distr.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    distr.time = np.array([1.0])
    distr.distribution.resize(1)
    distr.distribution[0].profiles_2d.resize(1)
    distr.distribution[0].profiles_2d[0].density = np.ones((2, 3))
    with pytest.raises(ValidationError):
        distr.validate()

    distr.distribution[0].profiles_2d[0].grid.r = np.linspace(0, 1, 2)
    distr.distribution[0].profiles_2d[0].grid.z = np.linspace(0, 1, 3)
    distr.validate()

    distr.distribution[0].profiles_2d[0].grid.rho_tor_norm = np.linspace(0, 1, 2)
    with pytest.raises(ValidationError):
        distr.validate()  # either grid/r or grid/rho_tor_norm can be defined

    distr.distribution[0].profiles_2d[0].grid.r = np.array([])
    distr.validate()


def test_validate_reference_or_fixed_size():
    waves = IDSFactory("3.39.0").waves()
    waves.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    waves.time = np.array([1.0])
    waves.coherent_wave.resize(1)
    waves.coherent_wave[0].beam_tracing.resize(1)
    waves.coherent_wave[0].beam_tracing[0].beam.resize(1)
    waves.validate()

    beam = waves.coherent_wave[0].beam_tracing[0].beam[0]
    # n_tor coordinate1=beam.length OR 1...1
    beam.wave_vector.n_tor = np.array([1], dtype=np.int32)
    waves.validate()
    beam.wave_vector.n_tor = np.array([1, 2], dtype=np.int32)
    with pytest.raises(ValidationError):
        waves.validate()  # beam.length has length 0
    beam.length = np.array([0.4, 0.5])
    waves.validate()


def test_validate_coordinate_same_as():
    ml = IDSFactory("3.39.0").mhd_linear()
    ml.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ml.time = np.array([1.0])
    ml.time_slice.resize(1)
    ml.validate()

    ml.time_slice[0].toroidal_mode.resize(1)
    tor_mode = ml.time_slice[0].toroidal_mode[0]
    tor_mode.plasma.grid.dim1 = np.ones(4)
    tor_mode.plasma.stress_maxwell.imaginary = np.ones((4, 5, 6))
    with pytest.raises(ValidationError):
        # The imaginary component has coordinate2/3_same_as the real component
        # but the real component is still empty
        ml.validate()

    tor_mode.plasma.stress_maxwell.real = np.ones((4, 5, 6))
    ml.validate()

    tor_mode.plasma.stress_maxwell.real = np.ones((4, 1, 6))
    with pytest.raises(ValidationError):
        ml.validate()  # dimension 2 does not match

    tor_mode.plasma.stress_maxwell.real = np.ones((4, 5, 1))
    with pytest.raises(ValidationError):
        ml.validate()  # dimension 3 does not match


@pytest.mark.parametrize(
    "env_value, should_validate",
    [
        ("1", False),
        ("yes", False),
        ("asdf", False),
        ("0", True),
        ("", True),
        (None, True),
    ],
)
def test_validate_on_put(monkeypatch, env_value, should_validate, requires_imas):
    dbentry = DBEntry(MEMORY_BACKEND, "test", 1, 1)
    dbentry.create()
    ids = dbentry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.time = np.array([1.0])

    validate_mock = Mock()
    monkeypatch.setattr("imas.ids_toplevel.IDSToplevel.validate", validate_mock)
    if env_value is None:
        monkeypatch.delenv("IMAS_AL_DISABLE_VALIDATE", raising=False)
    else:
        monkeypatch.setenv("IMAS_AL_DISABLE_VALIDATE", env_value)

    dbentry.put(ids)
    assert validate_mock.call_count == 1 * should_validate
    dbentry.put_slice(ids)
    assert validate_mock.call_count == 2 * should_validate


def test_validate_ignore_nested_aos():
    # Ignore coordinates inside an AoS outside our tree, see IMAS-4675
    equilibrium = IDSFactory("3.39.0").equilibrium()
    equilibrium.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    equilibrium.time = np.array([1.0])
    equilibrium.time_slice.resize(1)
    equilibrium.validate()
    equilibrium.time_slice[0].ggd.resize(1)
    # Coordinate of equilibrium time_slice(itime)/ggd = grids_ggd(itime)/grid
    # where grids_ggd is a (dynamic) AoS outside our tree, so this coordinate check
    # should be ignored:
    equilibrium.validate()


@pytest.fixture
def alternative_coordinates_cp():
    """Test alternative coordinates introduced in DDv4 with IMAS-4725."""
    cp = IDSFactory("4.0.0").new("core_profiles")
    cp.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    cp.profiles_1d.resize(1)
    cp.profiles_1d[0].time = 1.0
    cp.validate()
    return cp


# Alternatives for core_profiles profiles_1d/grid/rho_tor_norm
ALTERNATIVES = ["rho_tor_norm", "rho_tor", "psi", "volume", "area", "surface"]
ALTERNATIVES += ["rho_pol_norm"]


@pytest.fixture(params=ALTERNATIVES)
def alternative(request):
    return request.param


def test_single_alternative_coordinate_filled(alternative_coordinates_cp, alternative):
    alternative_coordinates_cp.profiles_1d[0].grid[alternative] = np.ones(3)
    alternative_coordinates_cp.validate()


def test_multiples_alternative_coordinates_filled(alternative_coordinates_cp):
    grid = alternative_coordinates_cp.profiles_1d[0].grid
    grid.rho_tor_norm = np.ones(3)
    grid.rho_tor = np.ones(2)
    with pytest.raises(ValidationError):
        alternative_coordinates_cp.validate()  # sizes don't match
    grid.rho_tor = np.ones(3)
    alternative_coordinates_cp.validate()  # now they match again

    # Add a third one
    grid.volume = np.ones(5)
    with pytest.raises(ValidationError):
        alternative_coordinates_cp.validate()  # sizes don't match
    grid.volume = np.ones(3)
    alternative_coordinates_cp.validate()  # now they match again


def test_validate_with_alternative_coordinates(alternative_coordinates_cp, alternative):
    grid = alternative_coordinates_cp.profiles_1d[0].grid
    alternative_coordinates_cp.profiles_1d[0].electrons.temperature = np.ones(4)
    with pytest.raises(ValidationError):
        alternative_coordinates_cp.validate()  # no coordinates allocated

    # Set to wrong size:
    grid[alternative] = np.ones(3)
    with pytest.raises(ValidationError):
        alternative_coordinates_cp.validate()
    # Now set to correct size
    grid[alternative] = np.ones(4)
    alternative_coordinates_cp.validate()


def test_validate_random_fill(ids_name):
    ids = IDSFactory().new(ids_name)
    fill_consistent(ids)
    ids.validate()
