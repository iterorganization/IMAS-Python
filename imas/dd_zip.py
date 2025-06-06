# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Extract DD versions from the imas-data-dictionaries distribution."""

import logging
import os
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

# These methods in imas_data_dictionaries used to be defined here. We import them here
# for backwards compatibility:
from imas_data_dictionaries import dd_identifiers  # noqa: F401
from imas_data_dictionaries import get_dd_xml_crc  # noqa: F401
from imas_data_dictionaries import get_identifier_xml  # noqa: F401
from imas_data_dictionaries import dd_xml_versions, get_dd_xml, parse_dd_version
from packaging.version import InvalidVersion

import imas
from imas.exception import UnknownDDVersion  # noqa: F401

logger = logging.getLogger(__name__)


# Expected use case is one, maximum two DD versions
# Cache is bigger than that: in pytest we currently use the following DD versions:
#   - 3.22.0
#   - 3.25.0
#   - 3.28.0
#   - 3.39.0
#   - 4.0.0 (if available)
#   - Environment default
#   - IDS_fake_toplevel.xml
#   - IDS_minimal.xml
#   - IDS_minimal_2.xml
#   - IDS_minimal_struct_array.xml
#   - IDS_minimal_types.xml
_DD_CACHE_SIZE = 8


def dd_etree(version=None, xml_path=None):
    """Return the DD element tree corresponding to the provided dd_version or xml_file.

    By default (``dd_version`` and ``dd_xml`` are not supplied), this will attempt
    to get the version from the environment (``IMAS_VERSION``) and use the latest
    available version as fallback.

    You can also specify a specific DD version to use (e.g. "3.38.1") or point to a
    specific data-dictionary XML file. These options are exclusive.

    Args:
        version: DD version string, e.g. "3.38.1".
        xml_path: XML file containing data dictionary definition.
    """
    if version and xml_path:
        raise ValueError("version and xml_path cannot be provided both.")
    if not version and not xml_path:
        # Figure out which DD version to use
        if "IMAS_VERSION" in os.environ:
            imas_version = os.environ["IMAS_VERSION"]
            if imas_version in dd_xml_versions():
                # Use bundled DD version when available
                version = imas_version
            elif "IMAS_PREFIX" in os.environ:
                # Try finding the IDSDef.xml in this installation
                imas_prefix = Path(os.environ["IMAS_PREFIX"]).resolve()
                xml_file = imas_prefix / "include" / "IDSDef.xml"
                if xml_file.exists():
                    xml_path = str(xml_file)
            if not version and not xml_path:
                logger.warning(
                    "Unable to load IMAS version %s, falling back to latest version.",
                    imas_version,
                )
    if not version and not xml_path:
        # Use latest available from
        version = latest_dd_version()
    # Do the actual loading in a cached method:
    return _load_etree(version, xml_path)


@lru_cache(_DD_CACHE_SIZE)
def _load_etree(version, xml_path):
    if xml_path:
        logger.info("Parsing data dictionary from file: %s", xml_path)
        tree = ET.parse(xml_path)
    else:
        xml = get_dd_xml(version)
        logger.info("Parsing data dictionary version %s", version)
        tree = ET.ElementTree(ET.fromstring(xml))
    return tree


def print_supported_version_warning(version):
    try:
        if parse_dd_version(version) < imas.OLDEST_SUPPORTED_VERSION:
            logger.warning(
                "Version %s is below lowest supported version of %s.\
                Proceed at your own risk.",
                version,
                imas.OLDEST_SUPPORTED_VERSION,
            )
    except InvalidVersion:
        logging.warning("Ignoring version parsing error.", exc_info=1)


def latest_dd_version():
    """Find the latest version in data-dictionary/IDSDef.zip"""
    return dd_xml_versions()[-1]
