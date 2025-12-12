# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.

from packaging.version import Version as _V

# Import logging _first_
# isort: off
from . import setup_logging  # noqa: F401

# isort: on

# Ensure that `imas.util` is loaded when importing imas
from . import util  # noqa: F401

# Public API:
from ._version import version as __version__
from ._version import version_tuple
from .convert_core_edge_plasma import (
    convert_to_plasma_profiles,
    convert_to_plasma_sources,
    convert_to_plasma_transport,
)
from .db_entry import DBEntry
from .ids_convert import convert_ids
from .ids_data_type import IDSDataType
from .ids_factory import IDSFactory
from .ids_identifiers import identifiers
from .ids_metadata import IDSMetadata, IDSType
from .ids_primitive import IDSPrimitive
from .ids_struct_array import IDSStructArray
from .ids_structure import IDSStructure
from .ids_toplevel import IDSToplevel

PUBLISHED_DOCUMENTATION_ROOT = "https://imas-python.readthedocs.io/en/latest/"
"""URL to the published documentation."""
OLDEST_SUPPORTED_VERSION = _V("3.22.0")
"""Oldest Data Dictionary version that is supported by IMAS-Python."""

__all__ = [
    "__version__",
    "version_tuple",
    "DBEntry",
    "IDSDataType",
    "IDSFactory",
    "IDSMetadata",
    "IDSPrimitive",
    "IDSStructure",
    "IDSStructArray",
    "IDSToplevel",
    "IDSType",
    "convert_ids",
    "convert_to_plasma_profiles",
    "convert_to_plasma_sources",
    "convert_to_plasma_transport",
    "identifiers",
    "PUBLISHED_DOCUMENTATION_ROOT",
    "OLDEST_SUPPORTED_VERSION",
]
