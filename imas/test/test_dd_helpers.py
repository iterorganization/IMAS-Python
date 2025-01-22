from pathlib import Path
import shutil
import pytest
import os
import zipfile

from imas.dd_helpers import prepare_data_dictionaries, _idsdef_zip_relpath, _build_dir

_idsdef_unzipped_relpath = Path("idsdef_unzipped")


def test_prepare_data_dictionaries():
    prepare_data_dictionaries()
    assert os.path.exists(
        _idsdef_zip_relpath
    ), f"IDSDef.zip file does not exist at path: {_idsdef_zip_relpath}"

    expected_xml_files = [
        _build_dir / "3.40.0.xml",
        _build_dir / "3.41.0.xml",
        _build_dir / "3.42.0.xml",
        _build_dir / "4.0.0.xml",
    ]

    for xml_file in expected_xml_files:
        assert os.path.exists(xml_file), f"{xml_file} does not exist"

    with zipfile.ZipFile(_idsdef_zip_relpath, "r") as zip_ref:
        zip_ref.extractall(_idsdef_unzipped_relpath)

    expected_ids_directories = [
        _idsdef_unzipped_relpath / "data-dictionary" / "3.40.0.xml",
        _idsdef_unzipped_relpath / "data-dictionary" / "3.41.0.xml",
        _idsdef_unzipped_relpath / "data-dictionary" / "3.42.0.xml",
        _idsdef_unzipped_relpath / "data-dictionary" / "4.0.0.xml",
        _idsdef_unzipped_relpath
        / "identifiers"
        / "core_sources"
        / "core_source_identifier.xml",
        _idsdef_unzipped_relpath
        / "identifiers"
        / "equilibrium"
        / "equilibrium_profiles_2d_identifier.xml",
    ]

    for file_path in expected_ids_directories:
        assert os.path.exists(
            file_path
        ), f"Expected_ids_directories {file_path} does not exist"

    if _build_dir.exists():
        shutil.rmtree(_idsdef_unzipped_relpath)


if __name__ == "__main__":
    pytest.main()
