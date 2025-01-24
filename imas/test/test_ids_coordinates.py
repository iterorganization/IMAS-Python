import numpy as np
import pytest

from imas.ids_coordinates import IDSCoordinate
from imas.ids_defs import IDS_TIME_MODE_HETEROGENEOUS, IDS_TIME_MODE_HOMOGENEOUS
from imas.ids_factory import IDSFactory


def test_coordinate_cache():
    coordinate = IDSCoordinate("1...N")
    coordinate2 = IDSCoordinate("1...N")
    assert coordinate is coordinate2


def test_coordinate_str_repr():
    coordinate = IDSCoordinate("test_coordinate")
    assert str(coordinate) == "test_coordinate"
    assert repr(coordinate) == "IDSCoordinate('test_coordinate')"


def test_coordinate_index_unbounded():
    coordinate = IDSCoordinate("1...N")
    assert coordinate.size is None
    assert not coordinate.references
    assert not coordinate.has_alternatives
    assert not coordinate.has_validation


@pytest.mark.parametrize("size", range(1, 5))
def test_coordinate_index_bounded(size):
    coordinate = IDSCoordinate(f"1...{size}")
    assert coordinate.size == size
    assert not coordinate.references
    assert coordinate.has_validation
    assert not coordinate.has_alternatives


def test_coordinate_with_path():
    coordinate = IDSCoordinate("time")
    assert coordinate.size is None
    assert len(coordinate.references) == 1
    assert str(coordinate.references[0]) == "time"
    assert coordinate.has_validation
    assert not coordinate.has_alternatives


def test_coordinate_with_multiple_paths():
    coordinate = IDSCoordinate(
        "distribution(i1)/profiles_2d(itime)/grid/r OR "
        "distribution(i1)/profiles_2d(itime)/grid/rho_tor_norm"
    )
    assert coordinate.size is None
    assert len(coordinate.references) == 2
    assert coordinate.has_validation
    assert coordinate.has_alternatives


def test_coordinate_with_path_or_size():
    coordinate = IDSCoordinate(
        "coherent_wave(i1)/beam_tracing(itime)/beam(i2)/length OR 1...1"
    )
    assert coordinate.size == 1
    assert len(coordinate.references) == 1
    assert coordinate.has_validation
    assert coordinate.has_alternatives


@pytest.mark.parametrize("spec", ["1...N_charge_states", "1..2"])
def test_coordinate_invalid(spec, caplog: pytest.LogCaptureFixture):
    with caplog.at_level("DEBUG", "imas.ids_coordinates"):
        caplog.clear()
        IDSCoordinate._cache.pop(spec, None)  # Remove spec from cache (if exists)
        coordinate = IDSCoordinate(spec)
        assert len(caplog.records) == 1
        assert not coordinate.has_validation


def test_coordinate_immutable():
    coordinate = IDSCoordinate("1...N")
    with pytest.raises(RuntimeError):
        coordinate.has_validation = True


def test_format_refs():
    core_profiles = IDSFactory(version="3.39.0").new("core_profiles")
    core_profiles.profiles_1d.resize(2)
    p1d = core_profiles.profiles_1d[1]
    refs = p1d.magnetic_shear.metadata.coordinate1.format_refs(p1d)
    assert refs == "`profiles_1d[1]/grid/rho_tor_norm`"

    distributions = IDSFactory(version="3.39.0").new("distributions")
    distributions.distribution.resize(2)
    distributions.distribution[1].profiles_2d.resize(5)
    p2d = distributions.distribution[1].profiles_2d[2]
    refs1 = p2d.density.metadata.coordinate1.format_refs(p2d)
    assert refs1 == (
        "`distribution[1]/profiles_2d[2]/grid/r`, "
        "`distribution[1]/profiles_2d[2]/grid/rho_tor_norm`"
    )
    refs2 = p2d.density.metadata.coordinate2.format_refs(p2d)
    assert refs2 == (
        "`distribution[1]/profiles_2d[2]/grid/z`, "
        "`distribution[1]/profiles_2d[2]/grid/theta_geometric`, "
        "`distribution[1]/profiles_2d[2]/grid/theta_straight`"
    )


def test_coordinates(ids_minimal_types):
    root = IDSFactory(xml_path=ids_minimal_types)
    ids = root.new("minimal")

    assert len(ids.flt_0d.coordinates) == 0
    assert len(ids.flt_1d.coordinates) == 1
    assert len(ids.flt_2d.coordinates) == 2
    assert len(ids.flt_3d.coordinates) == 3
    assert len(ids.flt_4d.coordinates) == 4
    assert len(ids.flt_5d.coordinates) == 5
    assert len(ids.flt_6d.coordinates) == 6

    ids.flt_1d = [1, 2, 4]
    assert ids.flt_1d.metadata.coordinates[0].size == 3
    assert all(ids.flt_1d.coordinates[0] == np.arange(3))

    ids.flt_3d = np.ones((3, 4, 2))
    assert ids.flt_3d.coordinates[0] is ids.flt_1d
    assert all(ids.flt_3d.coordinates[1] == np.arange(4))
    assert all(ids.flt_3d.coordinates[2] == np.arange(2))

    ids.cpx_1d = [1 - 1j]
    assert ids.cpx_1d.coordinates[0] is ids.flt_1d
    # if both flt_1d and int_1d are set, this should give an error
    ids.int_1d = [1]
    with pytest.raises(Exception):
        ids.cpx_1d.coordinates[0]


def test_coordinates_with_core_profiles():
    core_profiles = IDSFactory(version="3.39.0").new("core_profiles")
    with pytest.raises(ValueError):  # homogeneous_time not set
        core_profiles.profiles_1d.coordinates[0]

    core_profiles.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    assert core_profiles.profiles_1d.coordinates[0] is core_profiles.time

    core_profiles.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    # Test logic for getting time coordinates from inside the core_profiles AoS
    core_profiles.profiles_1d.resize(2)
    core_profiles.profiles_1d[0].time = 1
    core_profiles.profiles_1d[1].time = 2
    assert np.array_equal(core_profiles.profiles_1d.coordinates[0], [1.0, 2.0])


def test_coordinates_with_equilibrium():
    # Test error handling of a time-based coordinate outside our own timebasepath
    # https://jira.iter.org/browse/IMAS-4675
    equilibrium = IDSFactory(version="3.39.0").new("equilibrium")
    equilibrium.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    equilibrium.grids_ggd.resize(1)
    equilibrium.time_slice.resize(1)
    with pytest.raises(RuntimeError):
        equilibrium.time_slice[0].ggd.coordinates[0]


# TODO: test "<path> OR 1...1" coordinates: https://jira.iter.org/browse/IMAS-4661
# TODO: test complex amns_data coordinates: https://jira.iter.org/browse/IMAS-4666
