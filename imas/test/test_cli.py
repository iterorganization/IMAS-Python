from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from imas.command.cli import print_version, convert_ids
from imas.command.db_analysis import analyze_db, process_db_analysis
from imas.db_entry import DBEntry
from imas.test.test_helpers import fill_with_random_data


@pytest.mark.cli
def test_imas_version():
    runner = CliRunner()
    result = runner.invoke(print_version)
    assert result.exit_code == 0


@pytest.mark.cli
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


@pytest.mark.cli
def test_db_analysis_csv(tmp_path):
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


def test_imas_convert_with_plasma(tmp_path):
    in_db = tmp_path / "in"
    out_db = tmp_path / "out"
    with DBEntry(f"imas:hdf5?path={in_db}", "w", dd_version="3.39.0") as entry:
        for core_edge in ("core", "edge"):
            for suffix in ("profiles", "sources", "transport"):
                ids = entry.factory.new(f"{core_edge}_{suffix}")
                ids.ids_properties.homogeneous_time = 2
                for i in range(4):
                    ids.ids_properties.comment = f"{core_edge}_{suffix} occurrence {i}"
                    entry.put(ids, i)

    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        convert_result = runner.invoke(
            convert_ids,
            [
                "--convert-to-plasma-ids",
                f"imas:hdf5?path={in_db}",
                "4.1.0",
                f"imas:hdf5?path={out_db}",
            ],
        )
        assert convert_result.exit_code == 0

    with DBEntry(f"imas:hdf5?path={out_db}", "r", dd_version="4.1.0") as entry:
        for suffix in ("profiles", "sources", "transport"):
            for i in range(8):
                # We expect 8 occurrences, first 4 core, then 4 edge ones
                core_edge = "core" if i < 4 else "edge"
                expected_comment = f"{core_edge}_{suffix} occurrence {i % 4}"
                ids = entry.get(f"plasma_{suffix}", i)
                assert ids.ids_properties.comment == expected_comment


@pytest.mark.cli
def test_imas_convert_ids_list(tmp_path):
    in_db = tmp_path / "in"
    out_db = tmp_path / "out"
    with DBEntry(f"imas:hdf5?path={in_db}", "w", dd_version="3.39.0") as entry:
        for ids_name, occurrences in [
            ("core_profiles", 2),
            ("equilibrium", 1),
            ("summary", 1),
            ("wall", 1),
        ]:
            ids = entry.factory.new(ids_name)
            ids.ids_properties.homogeneous_time = 2
            for i in range(occurrences):
                entry.put(ids, i)

    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        convert_result = runner.invoke(
            convert_ids,
            [
                f"imas:hdf5?path={in_db}",
                "4.1.0",
                f"imas:hdf5?path={out_db}",
                "--ids",
                "core_profiles, equilibrium,core_profiles",
            ],
        )
        assert convert_result.exit_code == 0, convert_result.output

    with DBEntry(f"imas:hdf5?path={out_db}", "r", dd_version="4.1.0") as entry:
        assert entry.list_all_occurrences("core_profiles") == [0, 1]
        assert entry.list_all_occurrences("equilibrium") == [0]
        assert entry.list_all_occurrences("summary") == []
        assert entry.list_all_occurrences("wall") == []


@pytest.mark.cli
def test_imas_convert_unknown_ids(tmp_path):
    in_db = tmp_path / "in"
    out_db = tmp_path / "out"
    with DBEntry(f"imas:hdf5?path={in_db}", "w", dd_version="3.39.0") as entry:
        ids = entry.factory.core_profiles()
        ids.ids_properties.homogeneous_time = 2
        entry.put(ids)

    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        convert_result = runner.invoke(
            convert_ids,
            [
                f"imas:hdf5?path={in_db}",
                "4.1.0",
                f"imas:hdf5?path={out_db}",
                "--ids",
                "core_profiles,core_profile",
            ],
        )
    # A misspelled name is reported before anything is converted or written
    assert convert_result.exit_code == 2
    assert "unknown IDS name(s) for DD version 4.1.0: core_profile" in (
        convert_result.output
    )
    assert not out_db.exists()


def _write_occurrences(db_path, idss):
    with DBEntry(f"imas:hdf5?path={db_path}", "w", dd_version="3.39.0") as entry:
        for ids_name, occurrences in idss:
            ids = entry.factory.new(ids_name)
            ids.ids_properties.homogeneous_time = 2
            for i in range(occurrences):
                entry.put(ids, i)


@pytest.mark.cli
def test_imas_convert_ids_with_occurrences(tmp_path):
    in_db = tmp_path / "in"
    out_db = tmp_path / "out"
    _write_occurrences(in_db, [("core_profiles", 3), ("equilibrium", 2), ("wall", 1)])

    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        convert_result = runner.invoke(
            convert_ids,
            [
                f"imas:hdf5?path={in_db}",
                "4.1.0",
                f"imas:hdf5?path={out_db}",
                "--ids",
                "equilibrium, core_profiles:1,core_profiles:2,core_profiles:1",
            ],
        )
        assert convert_result.exit_code == 0, convert_result.output

    with DBEntry(f"imas:hdf5?path={out_db}", "r", dd_version="4.1.0") as entry:
        # An IDS without an occurrence converts all of them
        assert entry.list_all_occurrences("equilibrium") == [0, 1]
        assert entry.list_all_occurrences("core_profiles") == [1, 2]
        assert entry.list_all_occurrences("wall") == []


@pytest.mark.cli
def test_imas_convert_occurrence_option_is_deprecated(tmp_path):
    in_db = tmp_path / "in"
    out_db = tmp_path / "out"
    _write_occurrences(in_db, [("core_profiles", 3), ("equilibrium", 2)])

    runner = CliRunner()
    with patch("imas.command.cli.logger") as logger:
        with runner.isolated_filesystem(tmp_path):
            convert_result = runner.invoke(
                convert_ids,
                [
                    f"imas:hdf5?path={in_db}",
                    "4.1.0",
                    f"imas:hdf5?path={out_db}",
                    "--ids",
                    "core_profiles,equilibrium:0",
                    "--occurrence",
                    "2",
                ],
            )
            assert convert_result.exit_code == 0, convert_result.output
    assert any("deprecated" in str(c.args[0]) for c in logger.warning.call_args_list)

    with DBEntry(f"imas:hdf5?path={out_db}", "r", dd_version="4.1.0") as entry:
        # --occurrence still applies to IDSs given without an occurrence
        assert entry.list_all_occurrences("core_profiles") == [2]
        assert entry.list_all_occurrences("equilibrium") == [0]


@pytest.mark.cli
@pytest.mark.parametrize(
    "ids", ["core_profiles:x", "core_profiles:-1", "core_profiles:"]
)
def test_imas_convert_invalid_occurrence(tmp_path, ids):
    in_db = tmp_path / "in"
    out_db = tmp_path / "out"
    _write_occurrences(in_db, [("core_profiles", 1)])

    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        convert_result = runner.invoke(
            convert_ids,
            [
                f"imas:hdf5?path={in_db}",
                "4.1.0",
                f"imas:hdf5?path={out_db}",
                "--ids",
                ids,
            ],
        )
    assert convert_result.exit_code == 2
    assert "invalid occurrence" in convert_result.output
    assert not out_db.exists()
