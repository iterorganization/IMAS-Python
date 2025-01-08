# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Provides the classes for IDS data nodes
"""
import logging
import math
import operator
import struct
from copy import deepcopy
from numbers import Complex, Integral, Number, Real
from typing import Tuple

import numpy as np
from xxhash import xxh3_64, xxh3_64_digest

from imas.ids_base import IDSBase, IDSDoc
from imas.ids_coordinates import IDSCoordinates
from imas.ids_data_type import IDSDataType
from imas.ids_metadata import IDSMetadata

logger = logging.getLogger(__name__)


def _binary_wrapper(op, name):
    def func(self, other):
        if isinstance(other, IDSPrimitive):
            other = other.value
        return op(self.value, other)

    func.__name__ = f"__{name}__"
    return func


def _reflected_binary_wrapper(op, name):
    def func(self, other):
        if isinstance(other, IDSPrimitive):
            other = other.value
        return op(other, self.value)

    func.__name__ = f"__r{name}__"
    return func


def _numeric_wrapper(op, name):
    return (_binary_wrapper(op, name), _reflected_binary_wrapper(op, name))


def _unary_wrapper(op, name):
    def func(self):
        return op(self.value)

    func.__name__ = f"__{name}__"
    return func


class IDSPrimitive(IDSBase):
    """IDS leaf node

    Represents actual data. Examples are (arrays of) strings, floats, integers.
    Lives entirely in-memory until 'put' into a database.
    """

    __doc__ = IDSDoc(__doc__)
    __slots__ = ["_parent", "metadata", "__value"]

    def __init__(self, parent: IDSBase, metadata: IDSMetadata):
        """Initialize IDSPrimitive

        Args:
            parent: Parent node of this leaf
            metadata: IDSMetadata that describes this IDSPrimitive
        """
        self._parent = parent
        self.metadata = metadata

        self.__value = None

    @property
    def _lazy(self):
        """Whether this IDS Node is part of a lazy-loaded IDSToplevel"""
        return self._parent._lazy

    @property
    def coordinates(self):
        """Coordinates belonging to this quantity."""
        return IDSCoordinates(self)

    def __deepcopy__(self, memo):
        # note: if parent needs updating it is handled by the deepcopy of our parent
        # TODO: implement the statement on the previous line O_O
        copy = self.__class__(self._parent, self.metadata)
        copy.__value = deepcopy(self.__value, memo)
        return copy

    @property
    def shape(self) -> Tuple[int, ...]:
        """Get the shape of the contained data.

        For 0D data types, the shape is always an empty tuple.
        See also :external:py:func:`numpy.shape`.
        """
        if self.metadata.ndim == 0:
            return tuple()
        if self.__value is None:
            return (0,) * self.metadata.ndim
        return np.shape(self.__value)

    @property
    def size(self) -> int:
        """Get the size of stored data (number of elements stored).

        For 0D data types, the size is always 1 (even when set to the default).
        For 1+D data types, the size is the number of elements stored, see
        :external:py:attr:`numpy.ndarray.size`.
        """
        if self.metadata.ndim == 0:
            return 1
        if self.__value is None:
            return 0
        if self.metadata.data_type == IDSDataType.STR:
            return len(self.__value)
        # self.__value must be a numpy array
        return self.__value.size

    @property
    def has_value(self) -> bool:
        """True if a value is defined here that is not the default"""
        if self.__value is None:  # No value set
            return False
        return self.size > 0  # Default for ndarray and STR_1D types is size == 0

    def __len__(self) -> int:
        if self.metadata.ndim == 0:
            raise TypeError(f"IDS data node of type {self.data_type} has no len()")
        if self.__value is None:
            return 0
        return len(self.__value)

    @property
    def _default(self):
        data_type = self.metadata.data_type
        if self.metadata.ndim == 0:
            return data_type.default
        if data_type is IDSDataType.STR:
            return []
        return np.empty((0,) * self.metadata.ndim, dtype=data_type.numpy_dtype)

    def __iter__(self):
        return iter(self.value)

    def __repr__(self):
        empty = value_repr = ""
        if self.has_value:
            value_repr = f"\n{self.value.__class__.__qualname__}({self.value!r})"
        else:
            empty = "empty "
        return f"{self._build_repr_start()}, {empty}{self.data_type})>{value_repr}"

    @property
    def value(self):
        """Return the value of this IDSPrimitive if it is set,
        otherwise return the default"""
        if self.__value is None:
            if self.metadata.ndim == 0:
                return self._default
            # 1+D data types can be modified in-place, first set before returning so,
            # for example, `ids.time.value.resize(10)`` always works as expected.
            self.__value = self._default
        return self.__value

    @value.setter
    def value(self, setter_value):
        # NOTE: This setter is bypassed during a get/get_slice, and self.__value is set
        # directly.
        if self._lazy:
            raise ValueError("Lazy-loaded IDSs are read-only.")
        if isinstance(setter_value, type(self)):
            # No need to cast, just overwrite contained value
            if (
                setter_value.metadata.data_type is self.metadata.data_type
                and setter_value.metadata.ndim == self.metadata.ndim
            ):
                self.__value = setter_value.value
            # Can we cast the internal value to a valid value?
            else:
                self.__value = self._cast_value(setter_value.value)
        else:
            self.__value = self._cast_value(setter_value)
        if self.metadata.ndim == 0 and self.__value == self.metadata.data_type.default:
            # Unset 0D types when setting them to their magic default value
            self.__value = None

    # Implement special __dunder__ methods that just defer to the underlying value
    __eq__ = _binary_wrapper(operator.eq, "eq")
    __ne__ = _binary_wrapper(operator.ne, "ne")
    __lt__ = _binary_wrapper(operator.lt, "lt")
    __le__ = _binary_wrapper(operator.le, "le")
    __gt__ = _binary_wrapper(operator.gt, "gt")
    __ge__ = _binary_wrapper(operator.ge, "ge")
    __contains__ = _binary_wrapper(operator.contains, "contains")
    # Numeric methods
    __add__, __radd__ = _numeric_wrapper(operator.add, "add")
    __sub__, __rsub__ = _numeric_wrapper(operator.sub, "sub")
    __mul__, __rmul__ = _numeric_wrapper(operator.mul, "mul")
    __matmul__, __rmatmul__ = _numeric_wrapper(operator.matmul, "matmul")
    __truediv__, __rtruediv__ = _numeric_wrapper(operator.truediv, "truediv")
    __floordiv__, __rfloordiv__ = _numeric_wrapper(operator.floordiv, "floordiv")
    __mod__, __rmod__ = _numeric_wrapper(operator.mod, "mod")
    __divmod__, __rdivmod__ = _numeric_wrapper(divmod, "divmod")
    # TODO: handle the optional third argument for __pow__?
    __pow__, __rpow__ = _numeric_wrapper(operator.pow, "pow")
    __lshift__, __rlshift__ = _numeric_wrapper(operator.lshift, "lshift")
    __rshift__, __rrshift__ = _numeric_wrapper(operator.rshift, "rshift")
    __and__, __rand__ = _numeric_wrapper(operator.and_, "and")
    __xor__, __rxor__ = _numeric_wrapper(operator.xor, "xor")
    __or__, __ror__ = _numeric_wrapper(operator.or_, "or")
    # unary methods
    __neg__ = _unary_wrapper(operator.neg, "neg")
    __pos__ = _unary_wrapper(operator.pos, "pos")
    __abs__ = _unary_wrapper(operator.abs, "abs")
    __invert__ = _unary_wrapper(operator.invert, "invert")

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __getattr__(self, name):
        # Forward this getattr call to our actual value
        if not name.startswith("_"):
            return getattr(self.value, name)
        raise AttributeError(f"{self.__class__} object has no attribute {name}")

    def _cast_value(self, value):
        """Cast a value to the correct type.

        Must be implemented by subclasses.
        """
        raise NotImplementedError()

    @property
    def data_type(self):
        """Combine imas ids_type and ndims to AL data_type"""
        return "{!s}_{!s}D".format(self.metadata.data_type.value, self.metadata.ndim)

    def _validate(self) -> None:
        # Common validation logic
        super()._validate()
        # Validate coordinates
        if self.metadata.ndim > 0 and self.has_value:
            self.coordinates._validate()


_CONVERT_MSG = "Assigning incorrect type '%s' to %r, attempting automatic conversion."


def _cast_str(node, value):
    """Cast a value to a string.

    If value is a bytes object, decode it using UTF-8. Otherwise return str(value).
    """
    if not isinstance(value, str):
        logger.info(_CONVERT_MSG, type(value), node)
        if isinstance(value, bytes):
            return value.decode("UTF-8")
        return str(value)
    return value


class IDSString0D(IDSPrimitive):
    """IDSPrimitive specialization for STR_0D."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    _cast_value = _cast_str

    def __str__(self):
        return self.value

    def __len__(self):  # override as it is the only 0D quantity with a length
        return len(self.value)

    def _xxhash(self) -> bytes:
        return xxh3_64_digest(self.value.encode("UTF-8"))


class IDSString1D(IDSPrimitive):
    """IDSPrimitive specialization for STR_1D."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    def __getattr__(self, name):
        # Forward this getattr call to our actual value
        return getattr(self.value, name)

    def append(self, value):
        """Append a string to this list."""
        self.value.append(_cast_str(self, value))

    def extend(self, value):
        """Extend this list with an iterable of strings."""
        self.value.extend(_cast_str(self, val) for val in value)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            value = (_cast_str(self, val) for val in value)
        else:
            value = _cast_str(self, value)
        self.value[index] = value

    def _cast_value(self, value):
        if not isinstance(value, (str, bytes)):
            try:  # Try to iterate over value
                return list(_cast_str(self, val) for val in value)
            except TypeError:
                pass  # Just convert value to a string and store it as the only item
        if isinstance(value, str):
            logger.info(_CONVERT_MSG, type(value), self)
        return [_cast_str(self, value)]

    def _xxhash(self) -> bytes:
        hsh = xxh3_64(len(self).to_bytes(8, "little"))
        for s in self:
            hsh.update(xxh3_64_digest(s.encode("UTF-8")))
        return hsh.digest()


class IDSNumeric0D(IDSPrimitive):
    """Abstract base class for INT_0D, FLT_0D and CPX_0D."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    def __array__(self, dtype=None):
        return np.array(self.value, dtype=dtype)

    def __str__(self):
        return str(self.value)

    def _cast_value(self, value):
        if isinstance(value, np.ndarray) and value.ndim == 0:
            value = value.item()  # Unpack 0D numpy arrays
        cast_value = self.metadata.data_type.python_type(value)
        # nan != nan, so we need the second check to not complain when assigning a nan
        if cast_value != value and not (np.isnan(cast_value) and np.isnan(value)):
            logger.info(_CONVERT_MSG, type(value), self)
        return cast_value


class IDSComplex0D(IDSNumeric0D, Complex):
    """IDSPrimitive specialization for CPX_0D."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    def __complex__(self) -> complex:
        return self.value

    @property
    def real(self) -> float:
        return self.value.real

    @property
    def imag(self) -> float:
        return self.value.imag

    def conjugate(self) -> complex:
        return self.value.conjugate()

    def _xxhash(self) -> bytes:
        return xxh3_64_digest(struct.pack("<dd", self.real, self.imag))


class IDSFloat0D(IDSNumeric0D, Real):
    """IDSPrimitive specialization for FLT_0D."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    def __float__(self) -> float:
        return self.value

    def __int__(self) -> int:
        return int(self.value)

    def __trunc__(self) -> int:
        return int(self.value)

    def __floor__(self) -> int:
        return math.floor(self.value)

    def __ceil__(self) -> int:
        return math.ceil(self.value)

    def __round__(self, ndigits=None):
        return round(self.value, ndigits)

    def _xxhash(self) -> bytes:
        return xxh3_64_digest(struct.pack("<d", self.value))


class IDSInt0D(IDSNumeric0D, Integral):
    """IDSPrimitive specialization for INT_0D."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    def __int__(self):
        return self.value

    def __trunc__(self) -> int:
        return int(self.value)

    def __ceil__(self) -> int:
        return self.value

    def __floor__(self) -> int:
        return self.value

    def __round__(self, ndigits=None):
        return round(self.value, ndigits)

    def _xxhash(self) -> bytes:
        return xxh3_64_digest(self.value.to_bytes(4, "little", signed=True))


class IDSNumericArray(IDSPrimitive, np.lib.mixins.NDArrayOperatorsMixin):
    """IDSPrimitive specialization for ND numeric types (wrapping ``numpy.ndarray``)."""

    __doc__ = IDSDoc(__doc__)
    __slots__ = ()

    # One might also consider adding the built-in list type to this
    # list, to support operations like np.add(array_like, list)
    _HANDLED_TYPES = (np.ndarray, Number)

    def __array__(self, dtype=None):
        return self.value.astype(dtype, copy=False)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        out = kwargs.get("out", ())
        for x in inputs + out:
            # Only support operations with instances of _HANDLED_TYPES.
            # Use ArrayLike instead of type(self) for isinstance to
            # allow subclasses that don't override __array_ufunc__ to
            # handle ArrayLike objects.
            if not isinstance(x, self._HANDLED_TYPES + (IDSPrimitive,)):
                return NotImplemented

        # Defer to the implementation of the ufunc on unwrapped values.
        inputs = tuple(x.value if isinstance(x, IDSPrimitive) else x for x in inputs)
        if out:
            kwargs["out"] = tuple(
                x.value if isinstance(x, IDSPrimitive) else x for x in out
            )
        result = getattr(ufunc, method)(*inputs, **kwargs)

        if method == "at":
            # no return value
            return None
        else:
            # one return value
            return result

    def __repr__(self):
        # Specify that this is a numpy array, instead of a Python array As we
        # know .value is a numpy array, we can remove "array" part of the
        # numpy-native repr
        empty = value_repr = ""
        if self.has_value:
            value_repr = f"\n{_fullname(self.value)}{repr(self.value)[5:]}"
        else:
            empty = "empty "
        return f"{self._build_repr_start()}, {empty}{self.data_type})>{value_repr}"

    def _cast_value(self, value):
        dtype = self.metadata.data_type.numpy_dtype
        value = np.asanyarray(value)
        if value.dtype != dtype:
            logger.info(_CONVERT_MSG, value.dtype, self)
        value = np.array(value, dtype=dtype, copy=False)
        if value.ndim != self.metadata.ndim:
            raise ValueError(f"Trying to assign a {value.ndim}D value to {self!r}.")
        return value

    def _xxhash(self) -> bytes:
        arr = self.value
        hsh = xxh3_64(arr.ndim.to_bytes(1, "little"))
        hsh.update(struct.pack("<" + arr.ndim * "q", *arr.shape))
        # Ensure array is little endian, only create a copy if it is big-endian
        arr = arr.astype(arr.dtype.newbyteorder("little"), copy=False)
        hsh.update(arr.tobytes(order="F"))
        return hsh.digest()


def _fullname(o) -> str:
    """Get the full name to a type, including module name etc.

    Examples:
        - _fullname(np.array([1,2,3]) -> numpy.ndarray
        - fullname([1,2,3]) -> list
    """
    class_ = o.__class__
    module = class_.__module__
    if module == "builtins":
        return class_.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + class_.__qualname__
