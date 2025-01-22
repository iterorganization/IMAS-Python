# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Data Dictionary type handling functionality.
"""

from enum import Enum
from functools import lru_cache
from typing import Optional, Tuple

import numpy as np

from imas.ids_defs import (
    CHAR_DATA,
    COMPLEX_DATA,
    DOUBLE_DATA,
    EMPTY_COMPLEX,
    EMPTY_FLOAT,
    EMPTY_INT,
    INTEGER_DATA,
)


class IDSDataType(Enum):
    """Enum representing the possible data types in an IDS"""

    STRUCTURE = "structure"
    """IDS structure. Maps to an IDSStructure object."""

    STRUCT_ARRAY = "struct_array"
    """IDS array of structures. Maps to an IDSStructArray object with IDSStructure
    children."""

    STR = "STR"
    """String data."""

    INT = "INT"
    """Integer data."""

    FLT = "FLT"
    """Floating point data."""

    CPX = "CPX"
    """Complex data."""

    def __init__(self, value) -> None:
        self.default = {
            "STR": "",
            "INT": EMPTY_INT,
            "FLT": EMPTY_FLOAT,
            "CPX": EMPTY_COMPLEX,
        }.get(value, None)
        """Default value for a field with this type."""

        self.al_type = {
            "STR": CHAR_DATA,
            "INT": INTEGER_DATA,
            "FLT": DOUBLE_DATA,
            "CPX": COMPLEX_DATA,
        }.get(value, None)
        """Lowlevel identifier for this type."""

        self.python_type = {
            "STR": str,
            "INT": int,
            "FLT": float,
            "CPX": complex,
        }.get(value, None)
        """Python type for 0D instances of this type."""

        self.numpy_dtype = {
            "INT": np.int32,
            "FLT": np.float64,
            "CPX": np.complex128,
        }.get(value, None)
        """Numpy dtype for array instances of this type."""

    @staticmethod
    @lru_cache(maxsize=None)
    def parse(data_type: Optional[str]) -> Tuple[Optional["IDSDataType"], int]:
        """Parse data type string from the Data Dictionary.

        Args:
            data_type: Data type string from the DD.

        Returns:
            IDSDataType instance representing the parsed data type and number of
            dimensions.

        Examples:
            >>> IDSDataType.parse("STR_1D")
            (<IDSDataType.STR: 'STR'>, 1)
            >>> IDSDataType.parse("struct_array")
            (<IDSDataType.STRUCT_ARRAY: 'struct_array'>, 1)
            >>> IDSDataType.parse("structure")
            (<IDSDataType.STRUCTURE: 'structure'>, 0)
            >>> IDSDataType.parse("CPX_5D")
            (<IDSDataType.CPX: 'CPX'>, 5)
        """
        if data_type is None:
            return None, 0
        if data_type == "structure":
            ndim = 0
        elif data_type == "struct_array":
            ndim = 1
        else:
            dtype, *rest = data_type.upper().split("_")
            if rest == ["TYPE"]:  # legacy str_type, int_type, flt_type, cpx_type:
                ndim = 0
            elif rest and "0" <= rest[0][0] <= "9":
                # works for both legacy flt_1d_type and regular TYP_ND
                ndim = int(rest[0][0])
            else:
                raise ValueError(f"Unknown IDS data type: {data_type}")
            data_type = dtype
        return IDSDataType(data_type), ndim
