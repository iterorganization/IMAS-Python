import netCDF4
import pytest

from imaspy.backends.netcdf.nc2ids import NC2IDS
from imaspy.exception import InvalidNetCDFEntry
from imaspy.ids_factory import IDSFactory


@pytest.fixture()
def memfile():
    with netCDF4.Dataset("-", "w", diskless=True) as memfile:
        yield memfile


def test_invalid_homogeneous_time(memfile):
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

    ids = IDSFactory().core_profiles()
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(empty_group, ids)  # ids_properties.homogeneous_time does not exist
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(invalid_dtype, ids)
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(invalid_shape, ids)
    with pytest.raises(InvalidNetCDFEntry):
        NC2IDS(invalid_value, ids)
