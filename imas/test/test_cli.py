from pathlib import Path

import pytest
from click.testing import CliRunner

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
def test_db_analysis(tmp_path, requires_imas):
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


@pytest.mark.cli
def test_db_analysis_csv(tmp_path, requires_imas):
    with DBEntry(f"imas:hdf5?path={tmp_path}/entry1", "w") as entry:
        eq = entry.factory.equilibrium()
        eq.ids_properties.homogeneous_time = 2
        entry.put(eq)
        eq.ids_properties.comment = "filled"
        entry.put(eq, 1)
        eq.ids_properties.homogeneous_time = 1
        eq.time = [1.0]
        eq.time_slice.resize(1)
        eq.time_slice[0].boundary.psi = 1.0
        eq.time_slice[0].boundary.psi_error_upper = 0.1
        entry.put(eq, 2)
        wall = entry.factory.wall()
        wall.ids_properties.homogeneous_time = 2
        entry.put(wall)
        wall.first_wall_surface_area = 1.0
        entry.put(wall, 1)
    with DBEntry(f"imas:hdf5?path={tmp_path}/entry2", "w") as entry:
        eq = entry.factory.equilibrium()
        eq.ids_properties.homogeneous_time = 2
        eq.ids_properties.comment = "also filled"
        entry.put(eq)

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        analyze_result = runner.invoke(
            analyze_db, [f"{tmp_path}/entry1", f"{tmp_path}/entry2"]
        )
        assert analyze_result.exit_code == 0

        outfile = Path(td) / "imas-db-analysis.json.gz"
        assert outfile.exists()
        process_result = runner.invoke(
            process_db_analysis, [str(outfile), "--csv", "output.csv"]
        )
        assert process_result.exit_code == 0

        assert (
            Path("output.csv").read_text()
            == """\
IDS,Path in IDS,Uses errorbar,Frequency (without occurrences),Frequency (with occurences)
equilibrium,,,1.0,
equilibrium,ids_properties/comment,,1.0,0.75
equilibrium,ids_properties/homogeneous_time,,1.0,1.0
equilibrium,ids_properties/version_put/access_layer,,1.0,1.0
equilibrium,ids_properties/version_put/access_layer_language,,1.0,1.0
equilibrium,ids_properties/version_put/data_dictionary,,1.0,1.0
equilibrium,time,,0.5,0.25
equilibrium,time_slice/boundary/psi,X,0.5,0.25
wall,,,0.5,
wall,first_wall_surface_area,,1.0,0.5
wall,ids_properties/homogeneous_time,,1.0,1.0
wall,ids_properties/version_put/access_layer,,1.0,1.0
wall,ids_properties/version_put/access_layer_language,,1.0,1.0
wall,ids_properties/version_put/data_dictionary,,1.0,1.0
"""  # noqa: E501 (line too long)
        )
