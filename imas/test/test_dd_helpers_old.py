import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from imas.dd_helpers import transform_with_saxonche, build_data_dictionary
import logging


def test_transform_with_saxonche_success(tmp_path):
    """Test that transform_with_saxonche performs transformation successfully."""
    input_xml = tmp_path / "input.xml"
    xsl_file = tmp_path / "transform.xsl"
    output_file = tmp_path / "output.xml"

    # Create dummy input files
    input_xml.write_text("<root><child>Test</child></root>")
    xsl_file.write_text(
        """
    <xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
        <xsl:template match="/">
            <result><xsl:value-of select="root/child"/></result>
        </xsl:template>
    </xsl:stylesheet>
    """
    )

    transform_with_saxonche(input_xml, xsl_file, output_file)

    # Assert output
    assert output_file.exists()
    assert (
        output_file.read_text()
        == "<?xml version='1.0' encoding='UTF-8'?><result>Test</result>"
    )


def test_transform_with_saxonche_failure(tmp_path):
    """Test that transform_with_saxonche raises an error for invalid input."""
    input_xml = tmp_path / "input.xml"
    xsl_file = tmp_path / "transform.xsl"
    output_file = tmp_path / "output.xml"

    # Create invalid input files
    input_xml.write_text("<root><child>Test</child></root>")
    xsl_file.write_text("INVALID XSLT")

    with pytest.raises(Exception):
        transform_with_saxonche(input_xml, xsl_file, output_file)


@patch("imas.dd_helpers.repo")
@patch("imas.dd_helpers.transform_with_saxonche")
def test_build_data_dictionary(mock_transform, mock_repo, tmp_path):
    """Test build_data_dictionary function."""
    mock_repo.git.checkout = MagicMock()

    tag = "v1.0.0"
    result_xml = tmp_path / f"{tag}.xml"

    with patch("imas.dd_helpers._build_dir", tmp_path):
        build_data_dictionary(mock_repo, tag)

    # Verify the repo was checked out to the correct tag
    mock_repo.git.checkout.assert_called_once_with(tag, force=True)

    # Verify the transform_with_saxonche function was called
    mock_transform.assert_called_once()


def test_prepare_data_dictionaries(monkeypatch, tmp_path):
    """Integration test for prepare_data_dictionaries."""
    from imas.dd_helpers import prepare_data_dictionaries

    class MockRepo:
        tags = ["v3.21.2", "v3.22.0"]

        def git(self):
            return MagicMock()

    mock_repo = MockRepo()

    def mock_get_data_dictionary_repo():
        return mock_repo

    monkeypatch.setattr(
        "imas.dd_helpers.get_data_dictionary_repo", mock_get_data_dictionary_repo
    )

    with patch("imas.dd_helpers._build_dir", tmp_path):
        prepare_data_dictionaries()

    # Check that the expected output files are created
    assert len(list(tmp_path.glob("*.xml"))) == len(mock_repo.tags)
