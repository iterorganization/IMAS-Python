# A minimal testcase loading an IDS file and checking that the structure built is ok
from numbers import Complex, Integral, Number, Real

import numpy as np
import pytest

from imas.ids_data_type import IDSDataType
from imas.ids_factory import IDSFactory


@pytest.fixture
def minimal(ids_minimal_types):
    return IDSFactory(xml_path=ids_minimal_types).new("minimal")


# The test_assign_* tests are testing IDSPrimitive.cast_value
sample_values = {
    "str": ["0D string", ["list", "of", "strings"]],
    "int": [1, *(np.ones((2,) * i, dtype=np.int32) for i in range(1, 4))],
    "flt": [1.1, *(np.ones((2,) * i, dtype=np.float64) for i in range(1, 7))],
    "cpx": [
        1.1 + 1.1j,
        *(np.ones((2,) * i, dtype=np.complex128) * (1 + 1j) for i in range(1, 7)),
    ],
}


def test_assign_str_0d(minimal, caplog):
    caplog.set_level("INFO", "imas")

    # Test auto-encoding
    minimal.str_0d = b"123"
    assert minimal.str_0d.value == "123"
    assert len(caplog.records) == 1  # Should trigger a warning about auto-conversion

    for name, values in sample_values.items():
        for ndim, value in enumerate(values):
            caplog.clear()
            minimal.str_0d = value
            # All values except sample_values["str"][0] should log a warning
            assert len(caplog.records) == 0 if name == "str" and ndim == 0 else 1


def test_assign_str_1d(minimal, caplog):
    caplog.set_level("INFO", "imas")

    # Test auto-encoding
    minimal.str_1d = [b"123", "456"]
    assert minimal.str_1d.value == ["123", "456"]
    assert len(caplog.records) > 0  # Should trigger a warning about auto-conversion

    for name, values in sample_values.items():
        for ndim, value in enumerate(values):
            caplog.clear()
            minimal.str_1d = value
            # All values except sample_values["str"][1] should log a warning
            if name == "str" and ndim == 1:
                assert len(caplog.records) == 0
            else:
                assert len(caplog.records) > 0


# Prevent the expected numpy ComplexWarnings from cluttering pytest output
@pytest.mark.filterwarnings("ignore::numpy.ComplexWarning")
@pytest.mark.parametrize("typ, max_dim", [("flt", 6), ("cpx", 6), ("int", 3)])
def test_assign_numeric_types(minimal, caplog, typ, max_dim):
    caplog.set_level("INFO", "imas")
    for dim in range(max_dim + 1):
        name = f"{typ}_{dim}d"

        for other_typ, values in sample_values.items():
            can_assign = (
                other_typ == typ
                or (other_typ != "str" and typ == "cpx")  # Store float/int in complex
                or (other_typ == "flt" and typ == "int")  # Store float in int
                or (other_typ == "int" and typ == "flt")  # Store int in float
            )
            for other_ndim, value in enumerate(values):
                # We attempt to store other_typ (uppercase) with dimension other_ndim in
                # a variable of type typ (lowercase) and dimension dim
                if dim == other_ndim and can_assign:
                    caplog.clear()
                    minimal[name].value = value
                    if typ == other_typ or (dim == 0 and other_typ == "int"):
                        assert len(caplog.records) == 0
                    else:
                        len(caplog.records) == 1
                elif dim == other_ndim >= 1 and other_typ == "cpx":
                    # np allows casting of complex to float or int, but warns:
                    with pytest.warns(np.ComplexWarning):
                        caplog.clear()
                        minimal[name].value = value
                        assert len(caplog.records) == 1
                else:
                    with pytest.raises(Exception) as excinfo:
                        minimal[name].value = value
                    assert excinfo.type in (ValueError, TypeError)


def test_load_minimal_types(minimal):
    """Check if the standard datatypes are loaded correctly"""
    assert minimal.flt_0d.data_type == "FLT_0D"
    assert minimal.flt_1d.data_type == "FLT_1D"
    assert minimal.flt_2d.data_type == "FLT_2D"
    assert minimal.flt_3d.data_type == "FLT_3D"
    assert minimal.flt_4d.data_type == "FLT_4D"
    assert minimal.flt_5d.data_type == "FLT_5D"
    assert minimal.flt_6d.data_type == "FLT_6D"

    assert minimal.str_0d.data_type == "STR_0D"
    assert minimal.str_1d.data_type == "STR_1D"

    assert minimal.int_0d.data_type == "INT_0D"
    assert minimal.int_1d.data_type == "INT_1D"
    assert minimal.int_2d.data_type == "INT_2D"
    assert minimal.int_3d.data_type == "INT_3D"


def test_load_minimal_types_legacy(minimal):
    """Check if the legacy datatypes are loaded correctly"""
    assert minimal.flt_type.data_type == "FLT_0D"
    assert minimal.flt_1d_type.data_type == "FLT_1D"
    assert minimal.int_type.data_type == "INT_0D"
    assert minimal.str_type.data_type == "STR_0D"
    assert minimal.str_1d_type.data_type == "STR_1D"


def test_numeric_array_value(minimal):
    assert not minimal.flt_0d.has_value
    assert not minimal.flt_1d.has_value

    minimal.flt_0d.value = 7.4
    assert minimal.flt_0d.has_value

    minimal.flt_1d.value = [1.3, 3.4]
    assert minimal.flt_1d.has_value


@pytest.mark.parametrize("tp", ["flt_0d", "cpx_0d", "int_0d", "str_0d"])
def test_ids_primitive_properties_0d(minimal, tp):
    assert not minimal[tp].has_value
    assert minimal[tp].shape == tuple()
    assert minimal[tp].size == 1

    minimal[tp] = 1
    assert minimal[tp].has_value
    assert minimal[tp].shape == tuple()
    assert minimal[tp].size == 1

    minimal[tp] = minimal[tp].metadata.data_type.default
    assert not minimal[tp].has_value
    assert minimal[tp].shape == tuple()
    assert minimal[tp].size == 1


def test_ids_primitive_properties_str_1d(minimal):
    assert minimal.str_1d.shape == (0,)
    assert minimal.str_1d.size == 0
    assert not minimal.str_1d.has_value

    minimal.str_1d.value.append("1")
    assert minimal.str_1d.has_value
    assert minimal.str_1d.shape == (1,)
    assert minimal.str_1d.size == 1

    minimal.str_1d.value.pop()
    assert not minimal.str_1d.has_value
    assert minimal.str_1d.shape == (0,)
    assert minimal.str_1d.size == 0


@pytest.mark.parametrize("typ, max_dim", [("flt", 6), ("cpx", 6), ("int", 3)])
def test_ids_primitive_properties_numeric_arrays(minimal, typ, max_dim):
    for dim in range(1, max_dim + 1):
        tp = f"{typ}_{dim}d"

        assert not minimal[tp].has_value
        assert minimal[tp].shape == (0,) * dim
        assert minimal[tp].size == 0

        new_size = (2,) * dim
        minimal[tp].value = np.ones(new_size)
        assert minimal[tp].has_value
        assert minimal[tp].shape == new_size
        assert minimal[tp].size == 2**dim

        minimal[tp] = np.empty((0,) * dim)
        assert not minimal[tp].has_value
        assert minimal[tp].shape == (0,) * dim
        assert minimal[tp].size == 0


def test_ducktype_str0d(minimal):
    node = minimal.str_0d
    node.value = "Test"
    assert str(node) == "Test"
    assert len(node) == 4
    # Iteration
    assert list(node) == ["T", "e", "s", "t"]
    # A small selection of string manipulation functions
    assert node.upper() == "TEST"
    assert node.lower() == "test"
    assert node.split("e") == ["T", "st"]
    assert node.isprintable()
    assert node.replace("es", "eapo") == "Teapot"
    # Indexing and slicing
    assert node[:3] == "Tes"
    assert node[1:2] == node[1] == "e"
    # Arithmetic
    assert node + "!" == "Test!"
    assert node * 2 == 2 * node == "TestTest"
    # In place operation and __eq__
    minimal.str_0d += "X"
    assert node == node.value == "TestX"
    # Contains
    assert "estX" in node
    # Check we haven't accidentally replaced `node` with an actual string
    assert node is minimal.str_0d


def test_ducktype_str1d(minimal):
    node = minimal.str_1d
    assert len(node) == 0
    # List operations and functions
    node.append(1)
    assert node == ["1"]
    assert node.pop() == "1"
    assert bool(node) is False
    node[0:] = ["a", "b"]
    assert node == ["a", "b"]
    node.extend("cdefgh")
    assert node == list("abcdefgh")
    assert "d" in node
    # Indexing and slicing
    assert node[:3] == ["a", "b", "c"]
    assert node[4] == "e"
    node[5] = "X"
    assert node == list("abcdeXgh")
    # More functions
    assert node.count("X") == node.count("a") == 1
    assert len(node) == 8
    node.clear()
    assert node == []
    node.value = [1, 2]
    node.reverse()
    assert node == ["2", "1"]
    node.sort()
    assert node == ["1", "2"]
    # Iteration
    assert tuple(node) == ("1", "2")
    # Arithmetic
    assert node + ["3"] == list("123")
    assert node * 2 == 2 * node == list("1212")
    # Check we haven't accidentally replaced `node` with an actual list
    assert node is minimal.str_1d


def test_ducktype_int0d(minimal):
    node = minimal.int_0d
    node.value = 1
    assert node == 1
    assert int(node) == 1
    assert float(node) == 1.0
    assert complex(node) == 1.0 + 0.0j
    assert str(node) == "1"
    assert isinstance(node, Number)
    assert isinstance(node, Integral)
    # int functions/properties
    assert node.real == 1.0
    assert node.imag == 0.0
    assert node.bit_length() == 1
    assert node.to_bytes(1, "little") == b"\x01"
    # Arithmetic
    minimal.int_0d += 3
    assert node == 4
    assert +node == 4
    assert -node == -4
    assert bool(node) is True
    assert 2 * node == node * 2 == node + node == node + 4 == 4 + node == 8
    assert node - node == 0
    minimal.int_0d -= node
    assert node == 0
    assert bool(node) is False
    node.value = 2
    assert 3**node == 9
    assert node**3 == 8
    assert node / 3 == 2 / 3
    assert node // 3 == 0
    assert node % 3 == 2
    assert node << 1 == 4
    assert node >> 1 == 1
    assert 1 < node <= 2
    assert 2 <= node < 2.01
    node.value = 7
    assert divmod(node, 2) == (3, 1)
    assert divmod(10, node) == (1, 3)
    # Check we haven't accidentally replaced `node` with an actual int
    assert node is minimal.int_0d

    # Numpy operations
    assert np.array_equal(node, 7)
    assert np.isclose(node, 7)
    assert np.array(node).dtype.kind == "i"  # Don't care if int32 or int64


def test_ducktype_flt0d(minimal):
    node = minimal.flt_0d
    node.value = np.pi
    assert node == np.pi
    assert int(node) == 3
    assert float(node) == np.pi
    assert complex(node) == np.pi + 0.0j
    assert str(node) == str(np.pi)
    assert isinstance(node, Number)
    assert isinstance(node, Real)
    # float functions/properties
    assert node.real == np.pi
    assert node.imag == 0.0
    assert node.conjugate() == np.pi
    assert not node.is_integer()
    # Arithmetic
    assert +node == np.pi
    assert -node == -np.pi
    assert bool(node) is True
    twopi = 2 * np.pi
    assert 2 * node == node * 2 == node + node == node + np.pi == np.pi + node == twopi
    assert node - node == 0.0
    minimal.flt_0d -= node
    assert node == 0
    assert bool(node) is False
    node.value = 2
    assert isinstance(node.value, float)
    assert 3**node == 9
    assert node**3 == 8
    assert node / 3 == 2 / 3
    assert node // 3 == 0
    assert node % 3 == 2
    assert 1 < node <= 2
    assert 2 <= node < 2.01
    node.value = 7
    assert divmod(node, 2) == (3, 1)
    assert divmod(10, node) == (1, 3)
    # Check we haven't accidentally replaced `node` with an actual float
    assert node is minimal.flt_0d

    # Numpy operations
    assert np.array_equal(node, 7)
    assert np.isclose(node, 7)
    assert np.array(node).dtype == np.float64


def test_ducktype_cpx0d(minimal):
    node = minimal.cpx_0d
    node.value = 1.0 - 1.5j
    assert node == 1.0 - 1.5j
    assert complex(node) == 1.0 - 1.5j
    assert str(node) == str(1.0 - 1.5j)
    assert isinstance(node, Number)
    assert isinstance(node, Complex)
    # complex functions/properties
    assert node.real == 1.0
    assert node.imag == -1.5
    assert node.conjugate() == 1.0 + 1.5j
    # Arithmetic
    assert +node == 1.0 - 1.5j
    assert -node == -1.0 + 1.5j
    assert bool(node) is True
    assert 2 * node == node * 2 == node + node == 2.0 - 3.0j
    assert node + 1.0 == 1.0 + node == 2.0 - 1.5j
    assert node - node == 0
    minimal.cpx_0d -= node
    assert node == 0
    assert bool(node) is False
    node.value = 2.0 + 1j
    assert 3**node == 3 ** (2.0 + 1j)
    assert node**3 == (2.0 + 1j) ** 3
    assert node / 3 == 2 / 3 + 1j / 3
    # Check we haven't accidentally replaced `node` with an actual complex
    assert node is minimal.cpx_0d

    # Numpy operations
    assert np.array_equal(node, 2 + 1j)
    assert np.isclose(node, 2 + 1j)
    assert np.array(node).dtype == np.complex128


ducktype_params = []
for dtype in (IDSDataType.INT, IDSDataType.FLT, IDSDataType.CPX):
    for ndim in range(1, 4 if dtype is IDSDataType.INT else 7):
        value = np.ones((2,) * ndim, dtype=dtype.numpy_dtype)
        ducktype_params.append((f"{dtype.value}_{ndim}D", value))


@pytest.mark.parametrize("tp, val", ducktype_params)
def test_ducktype_ndarray(minimal, tp, val):
    node = minimal[tp.lower()]
    node.value = val
    # Numpy array properties
    assert node.shape == val.shape
    assert len(node) == len(val)
    assert node.ndim == val.ndim == node.metadata.ndim
    # Comparisons
    assert np.all(node == 1)
    assert not np.any(node != 1)
    assert np.all(0 < node)
    assert np.all(node <= 1)
    assert np.all(1 <= node)
    assert np.all(node < 2)
    # Some array functions
    assert node.all()
    assert node.min() == node.max() == node.mean() == 1.0
    assert node.std() == 0.0
    # Indexing
    assert np.array_equal(node[1], val[1])
    assert np.array_equal(node[:1], val[:1])
    # Arithmetic
    assert np.array_equal([1, 1] @ node, node @ [1, 1])
    assert np.array_equal([1, 1] @ node, [1, 1] @ val)
    assert np.array_equal(1 + node, node + 1)
    assert np.array_equal(node + 1, val + 1)
    assert np.array_equal(2 * node, node * 2)
    assert np.array_equal(2 * node, node + node)
    assert np.array_equal(2 * node, 2 * val)
    assert np.array_equal(node / 2, val / 2)
    assert np.array_equal(node * node, node**2)
    assert np.array_equal(node**2, val**2)
    if not tp.startswith("CPX"):
        assert np.array_equal(node // 2, val // 2)
    # Assignment
    node[(1,) * node.ndim] = 0
    assert node[(1,) * node.ndim] == 0
    # In place operation
    minimal[tp.lower()] += 2
    assert node[(0,) * node.ndim] == 3
    # Check we haven't accidentally replaced `node` with an actual numpy array
    assert node is minimal[tp.lower()]
