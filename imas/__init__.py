# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.

# isort: skip_file

from packaging.version import Version as _V

from ._version import version as __version__  # noqa: F401
from ._version import version_tuple  # noqa: F401

# Import logging _first_
from . import setup_logging

# Import main user API objects in the imas module
from .db_entry import DBEntry
from .ids_factory import IDSFactory
from .ids_convert import convert_ids
from .ids_identifiers import identifiers

# Load the imas-python IMAS AL/DD core
from . import (
    db_entry,
    dd_helpers,
    dd_zip,
    util,
)

PUBLISHED_DOCUMENTATION_ROOT = "https://imas-python.readthedocs.io/en/latest/"
"""URL to the published documentation."""
OLDEST_SUPPORTED_VERSION = _V("3.22.0")
"""Oldest Data Dictionary version that is supported by imas-python."""
