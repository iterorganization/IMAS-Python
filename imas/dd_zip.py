# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
""" Extract DD versions from a zip file.

The zip file contains files as
* `data-dictionary/3.30.0.xml`
* `data-dictionary/3.29.0.xml`

multiple paths are checked. See `ZIPFILE_LOCATIONS`.
First the environment variable IMAS_DDZIP is checked.
If that exists and points to a file we will attempt to open it.
Then, IDSDef.zip is searched in site-packages, the current folder,
in .config/imas/ (`$$XDG_CONFIG_HOME`) and in
the assets/ folder within the imas-python package.

1. `$$IMAS_DDZIP`
2. The virtual environment
3. USER_BASE`imas/IDSDef.zip`
4. All `site-packages/imas/IDSDef.zip`
5. `./IDSDef.zip`
6. `~/.config/imas/IDSDef.zip`
7. `__file__/../../imas/assets/IDSDef.zip`

All files are checked, i.e. if your .config/imas/IDSDef.zip is outdated
the imas-python-packaged version will be used.

The `assets/IDSDef.zip` provided with the package can be updated
with the `python setup.py build_DD` command, which is also performed on install
if you have access to the ITER data-dictionary git repo.
Reinstalling imas thus also will give you access to the latest DD versions.
"""
import logging
import os
import re
import xml.etree.ElementTree as ET
from contextlib import contextmanager, nullcontext
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterator, List, Tuple, Union
from zipfile import ZipFile

try:
    from importlib.resources import as_file, files

    try:
        from importlib.resources.abc import Traversable
    except ModuleNotFoundError:  # Python 3.9/3.10 support
        from importlib.abc import Traversable

except ImportError:  # Python 3.8 support
    from importlib_resources import as_file, files
    from importlib_resources.abc import Traversable

from packaging.version import InvalidVersion, Version

import imas
from imas.exception import UnknownDDVersion

logger = logging.getLogger(__name__)


def _get_xdg_config_dir():
    """
    Return the XDG config directory, according to the XDG base directory spec:

    https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
    """
    return os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")


def _generate_zipfile_locations() -> Iterator[Union[Path, Traversable]]:
    """Build a list of potential data dictionary locations.
    We start with the path (if any) of the IMAS_DDZIP env var.
    Then we look for IDSDef.zip in the current folder, in the
    default XDG config dir (~/.config/imas/IDSDef.zip) and
    finally in the assets distributed with this package.
    """
    zip_name = "IDSDef.zip"

    environ = os.environ.get("IMAS_DDZIP")
    if environ:
        yield Path(environ).resolve()

    yield Path(zip_name).resolve()
    yield Path(_get_xdg_config_dir()).resolve() / "imas" / zip_name
    yield files(imas) / "assets" / zip_name


def parse_dd_version(version: str) -> Version:
    try:
        return Version(version)
    except InvalidVersion:
        # This is probably a dev build of the DD, of which the version is obtained with
        # `git describe` in the format X.Y.Z-<ncommits>-g<hash> with X.Y.Z the previous
        # released version: try again after converting the first dash to a + and treat
        # it like a `local` version specifier, which is recognized as newer.
        # https://packaging.python.org/en/latest/specifications/version-specifiers/
        return Version(version.replace("-", "+", 1))


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
ZIPFILE_LOCATIONS = list(_generate_zipfile_locations())


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


@contextmanager
def _open_zipfile(path: Union[Path, Traversable]) -> Iterator[ZipFile]:
    """Open a zipfile, given a Path or Traversable."""
    if isinstance(path, Path):
        ctx = nullcontext(path)
    else:
        ctx = as_file(path)
    with ctx as file:
        with ZipFile(file) as zipfile:
            yield zipfile


@lru_cache
def _read_dd_versions() -> Dict[str, Tuple[Union[Path, Traversable], str]]:
    """Traverse all possible DD zip files and return a map of known versions.

    Returns:
        version_map: version -> (zipfile path, filename)
    """
    versions = {}
    xml_re = re.compile(r"^data-dictionary/([0-9.]+)\.xml$")
    for path in ZIPFILE_LOCATIONS:
        if not path.is_file():
            continue
        with _open_zipfile(path) as zipfile:
            for fname in zipfile.namelist():
                match = xml_re.match(fname)
                if match:
                    version = match.group(1)
                    if version not in versions:
                        versions[version] = (path, fname)
    if not versions:
        raise RuntimeError(
            "Could not find any data dictionary definitions. "
            f"Looked in: {', '.join(map(repr, ZIPFILE_LOCATIONS))}."
        )
    return versions


@lru_cache
def _read_identifiers() -> Dict[str, Tuple[Union[Path, Traversable], str]]:
    """Traverse all possible DD zip files and return a map of known identifiers.

    Returns:
        identifier_map: identifier -> (zipfile path, filename)
    """
    identifiers = {}
    xml_re = re.compile(r"^identifiers/\w+/(\w+_identifier).xml$")
    for path in ZIPFILE_LOCATIONS:
        if not path.is_file():
            continue
        with _open_zipfile(path) as zipfile:
            for fname in zipfile.namelist():
                match = xml_re.match(fname)
                if match:
                    identifier_name = match.group(1)
                    if identifier_name not in identifiers:
                        identifiers[identifier_name] = (path, fname)
    return identifiers


@lru_cache
def dd_xml_versions() -> List[str]:
    """Parse IDSDef.zip to find version numbers available"""

    def sort_key(version):
        try:
            return parse_dd_version(version)
        except InvalidVersion:
            # Don't fail when a malformatted version is present in the DD zip
            logger.error(
                f"Could not convert DD XML version {version} to a Version.", exc_info=1
            )
            return Version(0)

    return sorted(_read_dd_versions(), key=sort_key)


@lru_cache
def dd_identifiers() -> List[str]:
    """Parse IDSDef.zip to find available identifiers"""

    return sorted(_read_identifiers())


def get_dd_xml(version):
    """Read XML file for the given data dictionary version."""
    dd_versions = dd_xml_versions()
    if version not in dd_versions:
        raise UnknownDDVersion(version, dd_versions)
    path, fname = _read_dd_versions()[version]
    with _open_zipfile(path) as zipfile:
        return zipfile.read(fname)


def get_dd_xml_crc(version):
    """Given a version string, return its CRC checksum"""
    # Note, by this time get_dd_xml is already called, so we don't need to check if the
    # version is known
    path, fname = _read_dd_versions()[version]
    with _open_zipfile(path) as zipfile:
        return zipfile.getinfo(fname).CRC


def get_identifier_xml(identifier_name):
    """Get identifier XML for the given identifier name"""
    path, fname = _read_identifiers()[identifier_name]
    with _open_zipfile(path) as zipfile:
        return zipfile.read(fname)


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
