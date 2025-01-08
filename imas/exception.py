# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Exception classes used in imas-python.
"""

import difflib
import logging
from typing import TYPE_CHECKING, List

from imas.backends.imas_core import imas_interface as _imas_interface

if TYPE_CHECKING:
    from imas.ids_factory import IDSFactory


logger = logging.getLogger(__name__)


# Expose ALException, which may be thrown by the lowlevel
if _imas_interface.has_imas:
    ALException = _imas_interface.lowlevel.ALException
else:
    ALException = None


class UnknownDDVersion(ValueError):
    """Error raised when an unknown DD version is specified."""

    def __init__(self, version: str, available: List[str], note: str = "") -> None:
        close_matches = difflib.get_close_matches(version, available, n=1)
        if close_matches:
            suggestions = f"Did you mean {close_matches[0]!r}?"
        else:
            suggestions = f"Available versions are {', '.join(reversed(available))}"
        super().__init__(
            f"Data dictionary version {version!r} cannot be found. {suggestions}{note}"
        )


class IDSNameError(ValueError):
    """Error raised by DBEntry.get(_slice) when providing an invalid IDS name."""

    def __init__(self, ids_name: str, factory: "IDSFactory") -> None:
        suggestions = ""
        close_matches = difflib.get_close_matches(ids_name, factory.ids_names(), n=1)
        if close_matches:
            suggestions = f" Did you mean {close_matches[0]!r}?"
        super().__init__(f"IDS {ids_name!r} does not exist.{suggestions}")


class DataEntryException(RuntimeError):
    """Error raised by DBEntry for unexpected data in the backend."""


class MDSPlusModelError(RuntimeError):
    """Error raised when building MDS+ models."""

    def __init__(self, msg: str) -> None:
        super().__init__(f"Error building MDSplus data model: {msg}")


class LowlevelError(RuntimeError):
    """Error raised when lowlevel returns nonzero status"""

    def __init__(self, function: str, status: int):
        super().__init__(
            f"An Access Layer lowlevel operation ({function}) was unsuccessful "
            f"({status=}). "
            "More debug information should be available earlier in the program output."
        )


class CoordinateLookupError(Exception):
    """Error raised by IDSCoordinate.__getitem__ when a coordinate cannot be found."""


class ValidationError(Exception):
    """Error raised by IDSToplevel.validate() to indicate the IDS is not valid."""


class CoordinateError(ValidationError):
    """Error raised by ids.validate() to indicate a coordinate check has failed."""

    def __init__(self, node, dimension, expected_size, coor_path):
        """Create a new CoordinateError

        Args:
            node: IDSBase object that this coordinate error is raised for
            dimension: (0-based) dimension with incorrect size
            expected_size: size of the coordinate for the specified dimension
            coor_path: path of the coordinate, may be None when a coordinate is of fixed
                size (e.g. ``1...3``)
        """
        if coor_path is not None:  # Error message when coordinate size doesnt match
            details = (
                f"its coordinate in dimension {dimension + 1} (`{coor_path}`) has "
                f"size {expected_size}."
            )
        else:
            details = f"dimension {dimension + 1} must have size {expected_size}."
        super().__init__(
            f"Element `{node._path}` has incorrect shape {node.shape}: {details}"
        )


class InvalidNetCDFEntry(Exception):
    """Error raised when loading an IDS from a NetCDF file that fails validation."""
