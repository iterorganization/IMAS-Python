import pytest
from packaging.version import InvalidVersion

from imas.dd_zip import get_dd_xml, parse_dd_version
from imas.exception import UnknownDDVersion


def test_known_version():
    """Test if 3.30.0 is part of the IDSDef.zip
    Mostly this tests if IDSDef.zip has been made."""

    get_dd_xml("3.30.0")


def test_known_failing_version():
    """Test if 0.0 is not part of the IDSDef.zip"""

    with pytest.raises(UnknownDDVersion):
        get_dd_xml("0.0")


def test_parse_dd_version():
    release_version = parse_dd_version("3.39.0")
    dev_version = parse_dd_version("3.39.0-30-g7735675")
    assert dev_version > release_version
    dev_version2 = parse_dd_version("3.39.0-31-g7735675")
    assert dev_version2 > dev_version
    with pytest.raises(InvalidVersion):
        parse_dd_version("garbage")
