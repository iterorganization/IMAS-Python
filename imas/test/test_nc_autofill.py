from imas.db_entry import DBEntry
from imas.exception import InvalidNetCDFEntry
from imas.test.test_helpers import compare_children, fill_consistent
import re
import pytest
import netCDF4
from packaging import version


def test_nc_latest_dd_autofill_put_get_skip_complex(ids_name, tmp_path):
    with DBEntry(f"{tmp_path}/test-{ids_name}.nc", "x") as entry:
        ids = entry.factory.new(ids_name)
        fill_consistent(ids, leave_empty=0.5, skip_complex=True)

        entry.put(ids)
        ids2 = entry.get(ids_name)

    compare_children(ids, ids2)


@pytest.mark.skipif(
    version.parse(netCDF4.__version__) >= version.parse("1.7.0"),
    reason="NetCDF4 versions < 1.7.0 do not support complex numbers",
)
def test_nc_latest_dd_autofill_put_get_with_complex_older_netCDF4(ids_name, tmp_path):
    with DBEntry(f"{tmp_path}/test-{ids_name}.nc", "x") as entry:
        ids = entry.factory.new(ids_name)
        fill_consistent(ids, leave_empty=0.5, skip_complex=False)
        try:
            entry.put(ids)
            ids2 = entry.get(ids_name)
            compare_children(ids, ids2)
        except InvalidNetCDFEntry as e:
            # This is expected, as these versions of NetCDF4 do not support
            # complex numbers.
            if not re.search(
                r".*NetCDF 1.7.0 or later is required for complex data types", str(e)
            ):
                raise InvalidNetCDFEntry(e) from e


@pytest.mark.skipif(
    version.parse(netCDF4.__version__) < version.parse("1.7.0"),
    reason="NetCDF4 versions >= 1.7.0 support complex numbers",
)
def test_nc_latest_dd_autofill_put_get_with_complex_newer_netCDF4(ids_name, tmp_path):
    with DBEntry(f"{tmp_path}/test-{ids_name}.nc", "x") as entry:
        ids = entry.factory.new(ids_name)
        fill_consistent(ids, leave_empty=0.5, skip_complex=False)

        entry.put(ids)
        ids2 = entry.get(ids_name)

    compare_children(ids, ids2)
