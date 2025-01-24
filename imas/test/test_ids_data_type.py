import pytest

from imas.ids_data_type import IDSDataType


def test_legacy_type():
    assert IDSDataType.parse("str_type") == (IDSDataType.STR, 0)
    assert IDSDataType.parse("str_1d_type") == (IDSDataType.STR, 1)
    assert IDSDataType.parse("flt_type") == (IDSDataType.FLT, 0)
    assert IDSDataType.parse("flt_1d_type") == (IDSDataType.FLT, 1)
    assert IDSDataType.parse("int_type") == (IDSDataType.INT, 0)


@pytest.mark.parametrize("ndim", range(2))  # max string dimension is STR_1D
def test_str_types(ndim):
    assert IDSDataType.parse(f"STR_{ndim}D") == (IDSDataType.STR, ndim)


@pytest.mark.parametrize("ndim", range(4))  # max integer dimension is INT_3D
def test_int_types(ndim):
    assert IDSDataType.parse(f"INT_{ndim}D") == (IDSDataType.INT, ndim)


@pytest.mark.parametrize("ndim", range(7))  # max floatt dimension is FLT_6D
def test_flt_types(ndim):
    assert IDSDataType.parse(f"FLT_{ndim}D") == (IDSDataType.FLT, ndim)


@pytest.mark.parametrize("ndim", range(7))  # max complex dimension is CPX_6D
def test_cpx_types(ndim):
    assert IDSDataType.parse(f"CPX_{ndim}D") == (IDSDataType.CPX, ndim)


def test_default_values():
    assert IDSDataType.STR.default == ""
    assert IDSDataType.INT.default == -999_999_999
    assert IDSDataType.FLT.default == -9e40
    assert IDSDataType.CPX.default == -9e40 - 9e40j
    assert IDSDataType.STRUCT_ARRAY.default is None
    assert IDSDataType.STRUCTURE.default is None
