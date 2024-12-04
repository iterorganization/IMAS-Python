from pathlib import Path
from zlib import crc32

from imaspy import dd_zip
from imaspy.backends.imas_core.uda_support import extract_idsdef


def test_extract_idsdef():
    fname = extract_idsdef("4.0.0")
    expected_crc = dd_zip.get_dd_xml_crc("4.0.0")
    actual_crc = crc32(Path(fname).read_bytes())
    assert expected_crc == actual_crc
