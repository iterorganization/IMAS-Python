from pathlib import Path

import pytest
from click.testing import CliRunner
from packaging.version import Version

from imas.backends.imas_core.imas_interface import ll_interface
from imas.command.cli import print_version
from imas.command.db_analysis import analyze_db, process_db_analysis
from imas.db_entry import DBEntry
from imas.test.test_helpers import fill_with_random_data


@pytest.mark.cli
def test_imas_version():
    runner = CliRunner()
    result = runner.invoke(print_version)
    assert result.exit_code == 0


@pytest.mark.cli
@pytest.mark.skipif(ll_interface._al_version < Version("5.0"), reason="Needs AL >= 5")
def test_db_analysis(tmp_path):
    # This only tests the happy flow, error handling is not tested
    db_path = tmp_path / "test_db_analysis"
    with DBEntry(f"imas:hdf5?path={db_path}", "w") as entry:
        ids = entry.factory.core_profiles()
        fill_with_random_data(ids)
        entry.put(ids)

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        analyze_result = runner.invoke(analyze_db, [str(db_path)])
        assert analyze_result.exit_code == 0, analyze_result.output

    outfile = Path(td) / "imas-db-analysis.json.gz"
    assert outfile.exists()

    # Show detailed output for core_profiles, and then an empty input to exit cleanly:
    process_result = runner.invoke(
        process_db_analysis, [str(outfile)], input="core_profiles\n\n"
    )
    assert process_result.exit_code == 0, process_result.output
    assert "core_profiles" in process_result.output
