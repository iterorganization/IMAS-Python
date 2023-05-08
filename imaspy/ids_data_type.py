# This file is part of IMASPy.
# You should have received IMASPy LICENSE file with this project.
"""Logic for IDS data types.
"""
from enum import Enum
from typing import Tuple, Optional

from imaspy.ids_defs import EMPTY_INT, EMPTY_FLOAT, EMPTY_COMPLEX


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

    @staticmethod
    def parse(data_type: Optional[str]) -> Tuple[Optional["IDSDataType"], int]:
        """Parse data type string from the Data Dictionary.

        Args:
            data_type: Data type string from the DD.

        Returns:
            parsed_datatype: IDSDataType instance representing the parsed data type.
            ndim: number of dimensions.

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
            elif rest and '0' <= rest[0][0] <= '9':
                # works for both legacy flt_1d_type and regular TYP_ND
                ndim = int(rest[0][0])
            else:
                raise ValueError(f"Unknown IDS data type: {data_type}")
            data_type = dtype
        return IDSDataType(data_type), ndim
