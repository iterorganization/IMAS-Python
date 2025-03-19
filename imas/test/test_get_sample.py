import numpy as np
import pytest

import imas
from imas.backends.imas_core.imas_interface import lowlevel
from imas.exception import DataEntryException
from imas.ids_defs import (
    CLOSEST_INTERP,
    HDF5_BACKEND,
    IDS_TIME_MODE_HETEROGENEOUS,
    IDS_TIME_MODE_HOMOGENEOUS,
    LINEAR_INTERP,
    MDSPLUS_BACKEND,
    PREVIOUS_INTERP,
)


@pytest.fixture()
def test_db_uri(backend, worker_id, tmp_path_factory):
    # Check if begin_timerange_action is available in imas_core
    if not hasattr(lowlevel, "al_begin_timerange_action"):
        pytest.skip("imas_core version doesn't support begin_timerange_action.")

    # TODO: add MDSPLUS_BACKEND once implemented, see IMAS-5593
    if backend not in [HDF5_BACKEND]:
        pytest.skip("Backend doesn't support time range operations.")

    tmp_path = tmp_path_factory.mktemp(f"testdb.{worker_id}")
    backend_str = {HDF5_BACKEND: "hdf5", MDSPLUS_BACKEND: "mdsplus"}[backend]
    uri = f"imas:{backend_str}?path={tmp_path}"
    entry = imas.DBEntry(uri, "x", dd_version="4.0.0")

    # Homogeneous core profiles:
    cp = entry.factory.core_profiles()
    cp.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    N_time = 32
    cp.time = np.linspace(0, 1, N_time)
    cp.profiles_1d.resize(N_time)
    for i in range(N_time):
        # FLT_1D:
        cp.profiles_1d[i].grid.rho_tor_norm = np.array([0.0, 1.0])
        cp.profiles_1d[i].t_i_average = np.array([2.0, 1.0]) * (i + 1)
        cp.profiles_1d[i].ion.resize(1)
        # STR_0D:
        cp.profiles_1d[i].ion[0].name = "D"
        # FLT_0D
        cp.profiles_1d[i].ion[0].z_ion = 1.0
        cp.profiles_1d[i].ion[0].temperature = cp.profiles_1d[i].t_i_average
        # INT_0D
        cp.profiles_1d[i].ion[0].temperature_validity = 0
    cp.global_quantities.ip = (2 - cp.time) ** 0.5
    entry.put(cp)

    # Inhomogeneous equilibrium
    eq = entry.factory.equilibrium()
    eq.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    eq.time = np.linspace(0, 2, 512)
    # GGD Grid with 1 time slice
    eq.grids_ggd.resize(1)
    eq.grids_ggd[0].time = 0.0
    eq.grids_ggd[0].grid.resize(1)
    eq.grids_ggd[0].grid[0].path = "wall:0/description_ggd(1)/grid_ggd"
    # multiple time slices with data
    N_time = 6
    eq.time_slice.resize(N_time)
    for i in range(N_time):
        # FLT_0D
        eq.time_slice[i].time = i / 5.0
        eq.time_slice[i].profiles_2d.resize(1)
        # FLT_1D
        eq.time_slice[i].profiles_2d[0].grid.dim1 = np.array([0.0, 1.0])
        eq.time_slice[i].profiles_2d[0].grid.dim2 = np.array([3.0, 4.0])
        # STR_0D
        eq.time_slice[i].profiles_2d[0].grid_type.name = f"test {i}"
        eq.time_slice[i].profiles_2d[0].grid_type.description = "test description"
        # INT_0D
        eq.time_slice[i].profiles_2d[0].grid_type.index = -1
        # FLT_2D
        eq.time_slice[i].profiles_2d[0].r = np.array([[0.0, 0.0], [1.0, 1.0]])
        eq.time_slice[i].profiles_2d[0].z = np.array([[3.0, 4.0], [3.0, 4.0]])
        eq.time_slice[i].profiles_2d[0].psi = (
            eq.time_slice[i].profiles_2d[0].r - eq.time_slice[i].profiles_2d[0].z
        ) * (1 + eq.time_slice[i].time) ** 2
    entry.put(eq)

    # Equilibrium only has dynamic AOS and no other non-homogenous time nodes
    # Use magnetics to test that case:
    mag = entry.factory.magnetics()
    mag.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    mag.time = np.array([0.0])
    mag.flux_loop.resize(3)
    for i in range(3):
        mag.flux_loop[i].flux.time = np.linspace(0.0123, 1, 5 + i)
        mag.flux_loop[i].flux.data = 2 + 2 * mag.flux_loop[i].flux.time
        mag.flux_loop[i].voltage.time = np.linspace(0.0123, 1, 8 + i)
        mag.flux_loop[i].voltage.data = 2 - 5 * mag.flux_loop[i].voltage.time
    entry.put(mag)

    entry.close()
    return uri


@pytest.fixture()
def entry(test_db_uri):
    return imas.DBEntry(test_db_uri, "r", dd_version="4.0.0")


def test_invalid_arguments(entry):
    with pytest.raises(ValueError):
        entry.get_sample("core_profiles", 0.3, 0.2)  # tmin > tmax
    with pytest.raises(DataEntryException):
        entry.get_sample("core_profiles", 0.1, 0.2, occurrence="invalid")
    with pytest.raises(ValueError):
        entry.get_sample("core_profiles", 0.1, 0.2, 0.05)  # no interpolation method


def test_get_sample_homogeneous(entry):
    cp = entry.get_sample("core_profiles", 0.3, 14 / 31)
    assert np.array_equal(cp.time, np.linspace(0, 1, 32)[10:15])

    for i, p1d in enumerate(cp.profiles_1d):
        assert np.array_equal(p1d.grid.rho_tor_norm, [0.0, 1.0])
        assert np.array_equal(p1d.t_i_average, np.array([2.0, 1.0]) * (i + 11))
        assert len(p1d.ion) == 1
        assert p1d.ion[0].name == "D"
        assert p1d.ion[0].z_ion == 1
        assert np.array_equal(p1d.ion[0].temperature, p1d.t_i_average)
        assert p1d.ion[0].temperature_validity == 0

    assert np.array_equal(cp.global_quantities.ip, (2 - cp.time) ** 0.5)


def test_get_sample_heterogeneous(entry):
    eq = entry.get_sample("equilibrium", -1.0, 0.2)
    # Main time array
    assert np.array_equal(eq.time, np.linspace(0, 2, 512)[:52])
    # grids_ggd AoS
    assert len(eq.grids_ggd) == 1
    assert eq.grids_ggd[0].time == 0.0
    assert eq.grids_ggd[0].grid[0].path == "wall:0/description_ggd(1)/grid_ggd"
    # time_slice AoS
    assert len(eq.time_slice) == 2
    assert eq.time_slice[0].time == 0.0
    assert eq.time_slice[1].time == 0.2

    for i in range(2):
        p2d = eq.time_slice[i].profiles_2d[0]
        assert np.array_equal(p2d.grid.dim1, [0.0, 1.0])
        assert np.array_equal(p2d.grid.dim2, [3.0, 4.0])
        assert p2d.grid_type.name == f"test {i}"
        assert p2d.grid_type.index == -1
        assert np.array_equal(p2d.r, [[0.0, 0.0], [1.0, 1.0]])
        assert np.array_equal(p2d.z, [[3.0, 4.0], [3.0, 4.0]])
        expected_psi = (p2d.r - p2d.z) * (1 + eq.time_slice[i].time) ** 2
        assert np.array_equal(p2d.psi, expected_psi)

    mag = entry.get_sample("magnetics", 0.25, 0.75)
    assert mag.ids_properties.homogeneous_time == IDS_TIME_MODE_HETEROGENEOUS
    assert len(mag.time) == 0
    assert len(mag.flux_loop) == 3
    for i in range(3):
        fl = mag.flux_loop[i]

        flux_time = np.linspace(0.0123, 1, 5 + i)
        flux_time = flux_time[0.25 <= flux_time]
        flux_time = flux_time[flux_time <= 0.75]
        assert np.array_equal(fl.flux.time, flux_time)
        assert np.array_equal(fl.flux.data, 2 + 2 * flux_time)

        voltage_time = np.linspace(0.0123, 1, 8 + i)
        voltage_time = voltage_time[0.25 <= voltage_time]
        voltage_time = voltage_time[voltage_time <= 0.75]
        assert np.array_equal(fl.voltage.time, voltage_time)
        assert np.array_equal(fl.voltage.data, 2 - 5 * voltage_time)


def test_get_sample_homogeneous_linear_interp(entry):
    # Note requesting 0.401 and not 0.4, since
    # (0.3 + 0.02 + 0.02 + 0.02 + 0.02 + 0.02) = 0.4 + 5e-17
    cp = entry.get_sample("core_profiles", 0.3, 0.401, 0.02, LINEAR_INTERP)
    assert np.allclose(cp.time, np.linspace(0.3, 0.4, 6), rtol=1e-14, atol=0)

    assert len(cp.profiles_1d) == 6
    # Check some interpolated values
    for i in range(6):
        # Check rho_tor_norm
        rho_tor_norm = cp.profiles_1d[i].grid.rho_tor_norm
        assert np.array_equal(rho_tor_norm, np.array([0.0, 1.0]))
        # Check t_i_average
        expected = np.array([2.0, 1.0]) * (1 + 31 * cp.time[i])
        t_i_average = cp.profiles_1d[i].t_i_average
        assert np.allclose(t_i_average, expected, rtol=1e-14, atol=0)


def test_get_sample_homogeneous_explicit_timebase(entry):
    times = [0.1, 0.2345, 0.5, np.sqrt(2) / 2]
    cp = entry.get_sample("core_profiles", 0, 0, times, LINEAR_INTERP)
    assert np.allclose(cp.time, times, rtol=1e-14, atol=0)

    assert len(cp.profiles_1d) == 4
    # Check some interpolated values
    for i in range(4):
        # Check rho_tor_norm
        rho_tor_norm = cp.profiles_1d[i].grid.rho_tor_norm
        assert np.array_equal(rho_tor_norm, np.array([0.0, 1.0]))
        # Check t_i_average
        expected = np.array([2.0, 1.0]) * (1 + 31 * cp.time[i])
        t_i_average = cp.profiles_1d[i].t_i_average
        assert np.allclose(t_i_average, expected, rtol=1e-14, atol=0)


def test_get_sample_homogeneous_previous_interp(entry):
    # Note requesting 0.401 and not 0.4, since
    # (0.3 + 0.02 + 0.02 + 0.02 + 0.02 + 0.02) = 0.4 + 5e-17
    cp = entry.get_sample("core_profiles", 0.3, 0.401, 0.02, PREVIOUS_INTERP)
    assert np.allclose(cp.time, np.linspace(0.3, 0.4, 6), rtol=1e-14, atol=0)

    assert len(cp.profiles_1d) == 6
    # Check some interpolated values
    for i in range(6):
        # Check rho_tor_norm
        rho_tor_norm = cp.profiles_1d[i].grid.rho_tor_norm
        assert np.array_equal(rho_tor_norm, np.array([0.0, 1.0]))
        # Check t_i_average
        expected = np.array([2.0, 1.0]) * [10, 10, 11, 12, 12, 13][i]
        t_i_average = cp.profiles_1d[i].t_i_average
        assert np.allclose(t_i_average, expected, rtol=1e-14, atol=0)


def test_get_sample_homogeneous_closest_interp(entry):
    # Note requesting 0.401 and not 0.4, since
    # (0.3 + 0.02 + 0.02 + 0.02 + 0.02 + 0.02) = 0.4 + 5e-17
    cp = entry.get_sample("core_profiles", 0.3, 0.401, 0.02, CLOSEST_INTERP)
    assert np.allclose(cp.time, np.linspace(0.3, 0.4, 6), rtol=1e-14, atol=0)

    assert len(cp.profiles_1d) == 6
    # Check some interpolated values
    for i in range(6):
        # Check rho_tor_norm
        rho_tor_norm = cp.profiles_1d[i].grid.rho_tor_norm
        assert np.array_equal(rho_tor_norm, np.array([0.0, 1.0]))
        # Check t_i_average
        expected = np.array([2.0, 1.0]) * [10, 11, 12, 12, 13, 13][i]
        t_i_average = cp.profiles_1d[i].t_i_average
        assert np.allclose(t_i_average, expected, rtol=1e-14, atol=0)


def test_get_sample_heterogeneous_linear_interp(entry):
    eq = entry.get_sample("equilibrium", 0.2, 0.501, 0.05, LINEAR_INTERP)
    N_samples = 7
    # IDS becomes homogeneous after resampling
    assert np.allclose(eq.time, np.linspace(0.2, 0.5, N_samples))
    assert eq.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS

    # Check interpolated grids_ggd
    assert len(eq.grids_ggd) == N_samples
    for i in range(N_samples):
        # assert eq.grids_ggd[i].time == EMPTY_FLOAT
        assert len(eq.grids_ggd[i].grid) == 1
        assert eq.grids_ggd[i].grid[0].path == "wall:0/description_ggd(1)/grid_ggd"

    # Check interpolated time_slice
    assert len(eq.time_slice) == N_samples
    for i in range(N_samples):
        # assert eq.time_slice[i].time == EMPTY_FLOAT
        assert len(eq.time_slice[i].profiles_2d) == 1
        p2d = eq.time_slice[i].profiles_2d[0]
        assert np.array_equal(p2d.grid.dim1, [0.0, 1.0])
        assert np.array_equal(p2d.grid.dim2, [3.0, 4.0])

        # Determine the data as we have stored it in test_db_uri()
        time = eq.time[i]
        original_times = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        index = np.searchsorted(original_times, time)
        prevtime = original_times[index - 1]
        nexttime = original_times[index]
        prevpsi = (p2d.r - p2d.z) * (1 + prevtime) ** 2
        nextpsi = (p2d.r - p2d.z) * (1 + nexttime) ** 2
        # Linear interpolation
        expected_psi = (nextpsi * (time - prevtime) + prevpsi * (nexttime - time)) / (
            nexttime - prevtime
        )
        assert np.allclose(p2d.psi, expected_psi, rtol=1e-14, atol=0)

    mag = entry.get_sample("magnetics", 0.2, 0.501, 0.05, LINEAR_INTERP)
    assert mag.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS
    assert np.allclose(mag.time, np.linspace(0.2, 0.5, N_samples))

    assert len(mag.flux_loop) == 3
    for i in range(3):
        fl = mag.flux_loop[i]
        assert np.allclose(fl.flux.data, 2 + 2 * mag.time, rtol=1e-14, atol=0)
        assert np.allclose(fl.voltage.data, 2 - 5 * mag.time, rtol=1e-14, atol=2e-16)


def test_get_sample_heterogeneous_previous_interp(entry):
    eq = entry.get_sample("equilibrium", 0.2, 0.501, 0.05, PREVIOUS_INTERP)
    N_samples = 7
    # IDS becomes homogeneous after resampling
    assert np.allclose(eq.time, np.linspace(0.2, 0.5, N_samples))
    assert eq.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS

    # Check interpolated grids_ggd
    assert len(eq.grids_ggd) == N_samples
    for i in range(N_samples):
        # assert eq.grids_ggd[i].time == EMPTY_FLOAT
        assert len(eq.grids_ggd[i].grid) == 1
        assert eq.grids_ggd[i].grid[0].path == "wall:0/description_ggd(1)/grid_ggd"

    # Check interpolated time_slice
    assert len(eq.time_slice) == N_samples
    for i in range(N_samples):
        # assert eq.time_slice[i].time == EMPTY_FLOAT
        assert len(eq.time_slice[i].profiles_2d) == 1
        p2d = eq.time_slice[i].profiles_2d[0]
        assert np.array_equal(p2d.grid.dim1, [0.0, 1.0])
        assert np.array_equal(p2d.grid.dim2, [3.0, 4.0])

        origtime = [0.2, 0.2, 0.2, 0.2, 0.4, 0.4, 0.4][i]
        expected_psi = (p2d.r - p2d.z) * (1 + origtime) ** 2
        assert np.allclose(p2d.psi, expected_psi, rtol=1e-14, atol=0)

    mag = entry.get_sample("magnetics", 0.2, 0.501, 0.05, PREVIOUS_INTERP)
    assert mag.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS
    assert np.allclose(mag.time, np.linspace(0.2, 0.5, N_samples))

    assert len(mag.flux_loop) == 3
    for i in range(3):
        fl = mag.flux_loop[i]

        flux_time = np.linspace(0.0123, 1, 5 + i)
        flux_time = flux_time[np.searchsorted(flux_time, mag.time, side="right") - 1]
        assert np.array_equal(fl.flux.data, 2 + 2 * flux_time)

        voltage_time = np.linspace(0.0123, 1, 8 + i)
        voltage_time = voltage_time[
            np.searchsorted(voltage_time, mag.time, side="right") - 1
        ]
        assert np.array_equal(fl.voltage.data, 2 - 5 * voltage_time)


def test_get_sample_heterogeneous_closest_interp(entry):
    eq = entry.get_sample("equilibrium", 0.2, 0.501, 0.05, CLOSEST_INTERP)
    N_samples = 7
    # IDS becomes homogeneous after resampling
    assert np.allclose(eq.time, np.linspace(0.2, 0.5, N_samples))
    assert eq.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS

    # Check interpolated grids_ggd
    assert len(eq.grids_ggd) == N_samples
    for i in range(N_samples):
        # assert eq.grids_ggd[i].time == EMPTY_FLOAT
        assert len(eq.grids_ggd[i].grid) == 1
        assert eq.grids_ggd[i].grid[0].path == "wall:0/description_ggd(1)/grid_ggd"

    # Check interpolated time_slice
    assert len(eq.time_slice) == N_samples
    for i in range(N_samples):
        # assert eq.time_slice[i].time == EMPTY_FLOAT
        assert len(eq.time_slice[i].profiles_2d) == 1
        p2d = eq.time_slice[i].profiles_2d[0]
        assert np.array_equal(p2d.grid.dim1, [0.0, 1.0])
        assert np.array_equal(p2d.grid.dim2, [3.0, 4.0])

        # Note: CLOSEST appears to round up: 0.4 is closer to 0.3 than 0.2
        origtime = [0.2, 0.2, 0.4, 0.4, 0.4, 0.4, 0.6][i]
        expected_psi = (p2d.r - p2d.z) * (1 + origtime) ** 2
        assert np.allclose(p2d.psi, expected_psi, rtol=1e-14, atol=0)

    mag = entry.get_sample("magnetics", 0.2, 0.501, 0.05, CLOSEST_INTERP)
    assert mag.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS
    assert np.allclose(mag.time, np.linspace(0.2, 0.5, N_samples))

    assert len(mag.flux_loop) == 3
    for i in range(3):
        fl = mag.flux_loop[i]

        flux_time = np.linspace(0.0123, 1, 5 + i)
        flux_time = flux_time[
            np.argmin(np.abs(flux_time[None, :] - mag.time[:, None]), axis=1)
        ]
        assert np.array_equal(fl.flux.data, 2 + 2 * flux_time)

        voltage_time = np.linspace(0.0123, 1, 8 + i)
        voltage_time = voltage_time[
            np.argmin(np.abs(voltage_time[None, :] - mag.time[:, None]), axis=1)
        ]
        assert np.array_equal(fl.voltage.data, 2 - 5 * voltage_time)
