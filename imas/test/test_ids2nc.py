import netCDF4
import numpy
import pytest

from imas.backends.netcdf.ids2nc import IDS2NC, default_fillvals
from imas.ids_data_type import IDSDataType
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS
from imas.ids_factory import IDSFactory


@pytest.fixture
def group(tmp_path):
    with netCDF4.Dataset(tmp_path / "test.nc", "w") as group:
        yield group


def test_tensorization(group):
    ids = IDSFactory("3.39.0").core_profiles()

    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.time = [1.0, 2.0, 3.0]
    ids.profiles_1d.resize(3)
    for p1d in ids.profiles_1d:
        p1d.ion.resize(2)
        p1d.ion[0].label = "D"
        p1d.ion[0].z_ion = 1.0
        p1d.ion[0].element.resize(1)
        p1d.ion[0].element[0].a = 2.0
        p1d.ion[0].element[0].z_n = 1.0
        p1d.ion[0].element[0].atoms_n = 1

        p1d.ion[1].label = "OH-"
        p1d.ion[1].z_ion = -1.0
        p1d.ion[1].element.resize(2)
        p1d.ion[1].element[0].a = 1.0
        p1d.ion[1].element[0].z_n = 1.0
        p1d.ion[1].element[0].atoms_n = 1
        p1d.ion[1].element[1].a = 16.0
        p1d.ion[1].element[1].z_n = 8.0
        p1d.ion[1].element[1].atoms_n = 1

    IDS2NC(ids, group).run()
    # Test tensorized values
    expected = [["D", "OH-"]] * 3
    assert numpy.array_equal(group["profiles_1d.ion.label"], expected)
    assert not hasattr(group["profiles_1d.ion.label"], "sparse")

    expected = [[1.0, -1.0]] * 3
    assert numpy.array_equal(group["profiles_1d.ion.z_ion"], expected)
    assert not hasattr(group["profiles_1d.ion.z_ion"], "sparse")

    expected = [[[2.0, netCDF4.default_fillvals["f8"]], [1.0, 16.0]]] * 3
    assert numpy.array_equal(group["profiles_1d.ion.element.a"], expected)
    assert hasattr(group["profiles_1d.ion.element.a"], "sparse")

    expected = [[[1.0, netCDF4.default_fillvals["f8"]], [1.0, 8.0]]] * 3
    assert numpy.array_equal(group["profiles_1d.ion.element.z_n"], expected)
    assert hasattr(group["profiles_1d.ion.element.z_n"], "sparse")

    expected = [[[1, netCDF4.default_fillvals["i4"]], [1, 1]]] * 3
    assert numpy.array_equal(group["profiles_1d.ion.element.atoms_n"], expected)
    assert hasattr(group["profiles_1d.ion.element.atoms_n"], "sparse")

    # Test :shape arrays
    assert "profiles_1d:shape" not in group.variables
    assert not hasattr(group["profiles_1d"], "sparse")
    assert "profiles_1d.ion:shape" not in group.variables
    assert not hasattr(group["profiles_1d.ion"], "sparse")
    assert "profiles_1d.ion.element:shape" in group.variables
    # The shape array should be mentioned in the sparse attribute:
    assert "profiles_1d.ion.element:shape" in group["profiles_1d.ion.element"].sparse
    expected = [[[1], [2]]] * 3
    assert numpy.array_equal(group["profiles_1d.ion.element:shape"], expected)
    assert group["profiles_1d.ion.element:shape"].documentation != ""


def test_metadata(group):
    ids = IDSFactory("3.39.0").core_profiles()

    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.ids_properties.comment = "Test string variable"
    ids.time = [1.0, 2.0, 3.0]
    ids.profiles_1d.resize(3)
    for p1d in ids.profiles_1d:
        p1d.grid.rho_tor_norm = [0.0, 0.5, 1.0]
        p1d.j_tor = [1e3, 1e4, 1e5]

    IDS2NC(ids, group).run()

    for var in [
        "ids_properties",
        "ids_properties.homogeneous_time",
        "ids_properties.comment",
        "time",
        "profiles_1d",
        "profiles_1d.grid.rho_tor_norm",
        "profiles_1d.j_tor",
    ]:
        assert group[var].documentation == ids.metadata[var].documentation
        units = ids.metadata[var].units
        if units:
            assert group[var].units == units
        fillvalue = default_fillvals.get(ids.metadata[var].data_type)
        if fillvalue is None:
            assert ids.metadata[var].data_type in [
                IDSDataType.STRUCTURE,
                IDSDataType.STRUCT_ARRAY,
            ]
        else:
            assert group[var]._FillValue == fillvalue

    assert (
        group["profiles_1d.j_tor"].coordinates == "time profiles_1d.grid.rho_tor_norm"
    )


def test_filter_coordinates(group):
    ids = IDSFactory("3.39.0").pf_active()

    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.time = [1.0]
    ids.coil.resize(2)
    ids.coil[0].resistance = 1.0
    ids.coil[1].resistance = 2.0

    # Using sub-groups: IDS2NC expects an empty group to store the IDS in
    IDS2NC(ids, group.createGroup("1")).run()
    # coil.name or coil.identifier could be a coordinate, but they're not filled
    assert not hasattr(group["1/coil.resistance"], "coordinates")

    ids.coil[0].name = "coil 0"
    ids.coil[1].name = "coil 1"
    IDS2NC(ids, group.createGroup("2")).run()
    assert group["2/coil.resistance"].coordinates == "coil.name"

    ids.coil[0].identifier = "aab7b42a-5646-4f0a-8173-03dd5e4ad386"
    ids.coil[1].identifier = "aab7b42a-5646-4f0a-8173-283a57b3a801"
    IDS2NC(ids, group.createGroup("3")).run()
    assert group["3/coil.resistance"].coordinates == "coil.name coil.identifier"


def test_ancillary_variables(group):
    ids = IDSFactory("3.39.0").core_profiles()

    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.time = [1.0]
    ids.profiles_1d.resize(1)

    ids.profiles_1d[0].grid.rho_tor_norm = [0.0, 0.5, 1.0]
    ids.profiles_1d[0].j_tor = [1e2, 1e3, 1e4]
    ids.profiles_1d[0].j_tor_error_upper = [1e-1, 1e0, 1e1]
    ids.profiles_1d[0].j_total = [1e2, 1e3, 1e4]
    ids.profiles_1d[0].j_total_error_upper = [2e-1, 2e0, 2e1]
    ids.profiles_1d[0].j_total_error_lower = [1e-1, 1e0, 1e1]

    IDS2NC(ids, group).run()

    assert not hasattr(group["profiles_1d.grid.rho_tor_norm"], "ancillary_variables")
    assert (
        group["profiles_1d.j_tor"].ancillary_variables
        == "profiles_1d.j_tor_error_upper"
    )
    assert (
        group["profiles_1d.j_total"].ancillary_variables
        == "profiles_1d.j_total_error_upper profiles_1d.j_total_error_lower"
    )
