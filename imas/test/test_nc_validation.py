import netCDF4
import numpy as np
import pytest
from imas.backends.netcdf.ids2nc import IDS2NC
from imas.backends.netcdf.nc2ids import NC2IDS
from imas.backends.netcdf.nc_validate import validate_netcdf_file
from imas.exception import InvalidNetCDFEntry, UnknownDDVersion
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS
from imas.ids_factory import IDSFactory


@pytest.fixture()
def memfile():
    with netCDF4.Dataset("-", "w", diskless=True) as memfile:
        yield memfile


@pytest.fixture()
def factory():
    return IDSFactory("4.0.0")


@pytest.fixture()
def memfile_with_ids(memfile, factory):
    ids = factory.core_profiles()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.time = [1.0, 2.0, 3.0]
    ids.profiles_1d.resize(3)
    for i in range(3):
        ids.profiles_1d[i].grid.rho_tor_norm = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    ids.profiles_1d[0].zeff = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    IDS2NC(ids, memfile).run()
    # This one is valid:
    ids = factory.core_profiles()
    NC2IDS(memfile, ids, ids.metadata, None).run(lazy=False)
    return memfile


def test_invalid_homogeneous_time(memfile, factory):
    empty_group = memfile.createGroup("empty_group")
    # Invalid dtype
    invalid_dtype = memfile.createGroup("invalid_dtype")
    invalid_dtype.createVariable("ids_properties.homogeneous_time", float, ())[()] = 0
    # Invalid shape: 1D instead of 0D
    invalid_shape = memfile.createGroup("invalid_shape")
    invalid_shape.createDimension("dim")
    invalid_shape.createVariable("ids_properties.homogeneous_time", "i4", ("dim",))
    # Invalid value: not 0, 1 or 2
    invalid_value = memfile.createGroup("invalid_value")
    invalid_value.createVariable("ids_properties.homogeneous_time", "i4", ())

    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        # ids_properties.homogeneous_time does not exist
        NC2IDS(empty_group, ids, ids.metadata, None)
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(invalid_dtype, ids, ids.metadata, None)
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(invalid_shape, ids, ids.metadata, None)
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(invalid_value, ids, ids.metadata, None)


def test_invalid_units(memfile_with_ids, factory):
    memfile_with_ids["time"].units = "hours"
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_invalid_documentation(memfile_with_ids, factory, caplog):
    ids = factory.core_profiles()
    with caplog.at_level("WARNING"):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)
    assert not caplog.records
    # Invalid docstring logs a warning
    memfile_with_ids["time"].documentation = "https://en.wikipedia.org/wiki/Time"
    with caplog.at_level("WARNING"):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)
    assert len(caplog.records) == 1


def test_invalid_dimension_name(memfile_with_ids, factory):
    memfile_with_ids.renameDimension("time", "T")
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_invalid_coordinates(memfile_with_ids, factory):
    memfile_with_ids["profiles_1d.grid.rho_tor_norm"].coordinates = "xyz"
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_invalid_ancillary_variables(memfile_with_ids, factory):
    memfile_with_ids["time"].ancillary_variables = "xyz"
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_extra_attributes(memfile_with_ids, factory):
    memfile_with_ids["time"].new_attribute = [1, 2, 3]
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_shape_array_without_data(memfile_with_ids, factory):
    memfile_with_ids.createVariable("profiles_1d.t_i_average:shape", int, ())
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_shape_array_without_sparse_data(memfile_with_ids, factory):
    memfile_with_ids.createVariable("profiles_1d.grid.rho_tor_norm:shape", int, ())
    ids = factory.core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, ids, ids.metadata, None).run(lazy=False)


def test_shape_array_with_invalid_dimensions(memfile_with_ids, factory):
    cp = factory.core_profiles()
    t_i_average_meta = cp.metadata["profiles_1d.t_i_average"]
    t_i_average = memfile_with_ids.createVariable(
        "profiles_1d.t_i_average", float, ("time", "profiles_1d.grid.rho_tor_norm:i")
    )
    t_i_average.units = t_i_average_meta.units
    t_i_average.documentation = t_i_average_meta.documentation
    t_i_average.sparse = "Contents don't matter"
    memfile_with_ids.createVariable(
        "profiles_1d.t_i_average:shape",
        np.int32,
        ("time", "profiles_1d.grid.rho_tor_norm:i"),
    )
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, cp, cp.metadata, None).run(lazy=False)


def test_shape_array_with_invalid_dtype(memfile_with_ids, factory):
    cp = factory.core_profiles()
    t_i_average_meta = cp.metadata["profiles_1d.t_i_average"]
    t_i_average = memfile_with_ids.createVariable(
        "profiles_1d.t_i_average", float, ("time", "profiles_1d.grid.rho_tor_norm:i")
    )
    t_i_average.units = t_i_average_meta.units
    t_i_average.documentation = t_i_average_meta.documentation
    t_i_average.sparse = "Contents don't matter"
    memfile_with_ids.createVariable(
        "profiles_1d.t_i_average:shape", float, ("time", "1D")
    )
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(memfile_with_ids, cp, cp.metadata, None).run(lazy=False)


def test_validate_nc(tmpdir):
    fname = str(tmpdir / "test.nc")

    # Wrong extension
    with pytest.raises(InvalidNetCDFEntry):
        validate_netcdf_file("test.h5")  # invalid extension

    # Empty file
    netCDF4.Dataset(fname, "w").close()
    with pytest.raises(InvalidNetCDFEntry):
        validate_netcdf_file(fname)

    # Invalid DD version
    with netCDF4.Dataset(fname, "w") as dataset:
        dataset.data_dictionary_version = "invalid"
        dataset.createGroup("core_profiles")
    with pytest.raises(UnknownDDVersion):
        validate_netcdf_file(fname)

    # Invalid group
    with netCDF4.Dataset(fname, "w") as dataset:
        dataset.data_dictionary_version = "4.0.0"
        dataset.createGroup("X")
    with pytest.raises(InvalidNetCDFEntry):
        validate_netcdf_file(fname)

    # Invalid occurrence
    with netCDF4.Dataset(fname, "w") as dataset:
        dataset.data_dictionary_version = "4.0.0"
        dataset.createGroup("core_profiles/a")
    with pytest.raises(InvalidNetCDFEntry):
        validate_netcdf_file(fname)

    # Invalid variable in root group
    with netCDF4.Dataset(fname, "w") as dataset:
        dataset.data_dictionary_version = "4.0.0"
        dataset.createVariable("core_profiles", int, ())
    with pytest.raises(InvalidNetCDFEntry):
        validate_netcdf_file(fname)

    # Missing ids_properties.homogeneous_time
    with netCDF4.Dataset(fname, "w") as dataset:
        dataset.data_dictionary_version = "4.0.0"
        dataset.createGroup("core_profiles/1")
    with pytest.raises(InvalidNetCDFEntry):
        validate_netcdf_file(fname)

    # All other validations are handled by NC2IDS and tested above
