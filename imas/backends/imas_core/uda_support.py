import logging
from pathlib import Path
from typing import Union
from xml.etree import ElementTree as ET

from imas import dd_zip

from .mdsplus_model import _get_xdg_cache_dir

logger = logging.getLogger(__name__)


def get_dd_version_from_idsdef_xml(path: Union[str, Path]) -> str:
    """Parse the IDSDef.xml up to the point where the Data Dictionary version is set.

    Returns:
        The Data Dictionary version for the provided file, or None if the file cannot be
        parsed / contains no Data Dictionary version.
    """
    try:
        for _, elem in ET.iterparse(path):
            if elem.tag == "version":
                return elem.text
    except OSError:
        pass  # File not found, etc.
    except Exception:
        logger.warning("Could not read DD version from file '%s'.", path, exc_info=True)
    return None


def extract_idsdef(dd_version: str) -> str:
    """Extract the IDSDef.xml for the given version and return its path.

    The IDSDef.xml is extracted to the imas cache folder:

    - If the file imas/uda/<version>.xml already exists, we assume it is correct
    """
    cache_dir_path = Path(_get_xdg_cache_dir()) / "imas" / "uda"
    cache_dir_path.mkdir(parents=True, exist_ok=True)  # ensure cache folder exists
    idsdef_path = cache_dir_path / (dd_version + ".xml")

    if idsdef_path.exists():
        extract = False
        # Check if the file is fine
        if get_dd_version_from_idsdef_xml(idsdef_path) != dd_version:
            # File is corrupt, I guess? We'll overwrite:
            extract = True
    else:
        extract = True

    if extract:
        # Extract XML from the dd_zip and store
        data = dd_zip.get_dd_xml(dd_version)
        idsdef_path.write_bytes(data)

    return str(idsdef_path)
