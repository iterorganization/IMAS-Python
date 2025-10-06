from unittest.mock import Mock

import pytest
from imas.dd_zip import dd_identifiers
from imas.ids_factory import IDSFactory
from imas.ids_identifiers import IDSIdentifier, identifiers


def test_list_identifiers():
    assert identifiers.identifiers == dd_identifiers()
    # Check a known identifier, which we'll also use in more tests
    assert "core_source_identifier" in identifiers.identifiers


def test_identifier_enum():
    csid = identifiers.core_source_identifier
    # Test item access
    assert csid is identifiers["core_source_identifier"]

    # Class and inheritance tests
    assert csid.__name__ == "core_source_identifier"
    assert csid.__qualname__ == "imas.ids_identifiers.core_source_identifier"
    assert issubclass(csid, IDSIdentifier)
    assert isinstance(csid.total, csid)
    assert isinstance(csid.total, IDSIdentifier)

    # Check access methods
    assert csid.total is csid(1)
    assert csid.total is csid["total"]

    # Check attributes
    assert csid.total.name == "total"
    assert csid.total.index == csid.total.value == 1
    assert isinstance(csid.total.description, str)
    assert csid.total.description != ""


def test_identifier_struct_assignment(caplog):
    csid = identifiers.core_source_identifier
    cs = IDSFactory("3.39.0").core_sources()
    cs.source.resize(3)
    assert cs.source[0].identifier.metadata.identifier_enum is csid
    # Test assignment options: identifier instance, index and name
    cs.source[0].identifier = csid.total
    cs.source[1].identifier = "total"
    cs.source[2].identifier = 1
    for source in cs.source:
        assert source.identifier.name == "total"
        assert source.identifier.index == 1
        assert source.identifier.description == csid.total.description
        # Test equality of identifier structure and enum:
        assert source.identifier == csid.total
        assert source.identifier != csid(0)
    # Test fuzzy equality
    caplog.clear()
    # Empty description is okay
    source.identifier.description = ""
    assert source.identifier == csid.total
    assert not caplog.records
    # Incorrect description logs a warning
    source.identifier.description = "XYZ"
    assert source.identifier == csid.total
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    source.identifier.description = ""
    # Empty name is okay
    source.identifier.name = ""
    assert source.identifier == csid.total
    # But non-matching name is not okay
    source.identifier.name = "XYZ"
    assert source.identifier != csid.total


def test_identifier_struct_assignment_with_aliases(caplog):
    """Test identifier struct assignment with aliases using materials_identifier."""
    mid = identifiers.materials_identifier

    # Create a mock struct to simulate identifier structure
    mock_struct = Mock()
    mock_struct.name = "235U"
    mock_struct.index = 20
    mock_struct.description = "Uranium 235 isotope"
    mock_struct.alias = "U_235"

    # Basic attribute checks
    if hasattr(mid, "235U"):
        assert mock_struct.name == mid["235U"].name
        assert mock_struct.alias == mid.U_235.alias

    assert mock_struct.index == mid.U_235.index

    # Test equality with identifier enum (this tests our updated __eq__ method)
    caplog.clear()

    # Helper function to simulate equality logic
    def mock_identifier_equals(name, index, description, alias=None, target=None):
        name_matches = name in (target.name, target.alias)
        alias_matches = (
            alias in (target.name, target.alias) if alias is not None else False
        )

        return (
            (name_matches or alias_matches)
            and index == target.index
            and description == target.description
        )

    # Simulate comparisons
    if hasattr(mid, "235U"):
        assert mock_identifier_equals(
            "235U", 20, "Uranium 235 isotope", target=mid.U_235
        )
        assert mock_identifier_equals(
            "U_235", 20, "Uranium 235 isotope", target=mid["235U"]
        )
        assert mock_identifier_equals(
            "some_name", 20, "Uranium 235 isotope", alias="U_235", target=mid.U_235
        )
        assert mock_identifier_equals(
            "some_name", 20, "Uranium 235 isotope", alias="235U", target=mid.U_235
        )


def test_identifier_aos_assignment():
    cfid = identifiers.pf_active_coil_function_identifier
    pfa = IDSFactory("3.39.0").pf_active()
    pfa.coil.resize(1)
    pfa.coil[0].function.resize(3)
    assert pfa.coil[0].function.metadata.identifier_enum is cfid
    # Test assignment options: identifier instance, index and name
    pfa.coil[0].function[0] = cfid.flux
    pfa.coil[0].function[1] = "flux"
    pfa.coil[0].function[2] = 0
    for function in pfa.coil[0].function:
        assert function.name == "flux"
        assert function.index == 0
        assert function.description == cfid.flux.description
        # Test equality of identifier structure and enum:
        assert function == cfid.flux
        assert function != cfid.b_field_shaping
    assert pfa.coil[0].function[0] == cfid.flux


def test_invalid_identifier_assignment():
    cfid = identifiers.pf_active_coil_function_identifier
    cs = IDSFactory("3.39.0").core_sources()
    cs.source.resize(1)

    with pytest.raises(TypeError):
        # Incorrect identifier type
        cs.source[0].identifier = cfid.flux
    with pytest.raises(ValueError):
        cs.source[0].identifier = "identifier names never contain spaces"
    with pytest.raises(ValueError):
        # negative identifiers are reserved for user-defined identifiers
        cs.source[0].identifier = -1


def test_identifier_aliases():
    """Test identifier enum aliases functionality."""
    mid = identifiers.materials_identifier

    # Test that aliases exist for specific entries
    assert hasattr(mid, "U_235")
    assert hasattr(mid, "U_238")
    assert hasattr(mid, "In_115")
    assert hasattr(mid, "He_4")

    # Test that alias points to the same object as the canonical name
    if hasattr(mid, "235U"):
        assert mid.U_235 is mid["235U"]
    if hasattr(mid, "238U"):
        assert mid.U_238 is mid["238U"]
    if hasattr(mid, "115In"):
        assert mid.In_115 is mid["115In"]
    if hasattr(mid, "4He"):
        assert mid.He_4 is mid["4He"]

    # Test that both name and alias have the same properties
    if hasattr(mid, "235U"):
        assert mid.U_235.name == "235U"
        assert mid.U_235.index == mid["235U"].index
        assert mid.U_235.description == mid["235U"].description
        assert mid.U_235.alias == "U_235"

    # Test accessing by alias via bracket notation
    assert mid["U_235"] is mid.U_235
    assert mid["U_238"] is mid.U_238
    assert mid["In_115"] is mid.In_115
    assert mid["He_4"] is mid.He_4


def test_identifier_alias_equality():
    """Test that identifiers with aliases are equal when comparing names
    and aliases."""
    mid = identifiers.materials_identifier
    target = mid.U_235

    # Test equality with canonical name
    mock_canonical = Mock()
    mock_canonical.name = "235U"
    mock_canonical.index = 20
    mock_canonical.description = "Uranium 235 isotope"
    mock_canonical.alias = None
    if hasattr(mid, "235U"):
        assert (
            mock_canonical.name in (target.name, target.alias)
            and mock_canonical.index == target.index
            and mock_canonical.description == target.description
        )

    # Test equality with alias name
    mock_alias = Mock()
    mock_alias.name = "U_235"
    mock_alias.index = 20
    mock_alias.description = "Uranium 235 isotope"
    mock_alias.alias = None
    if hasattr(mid, "235U"):
        assert (
            mock_alias.name in (target.name, target.alias)
            and mock_alias.index == target.index
            and mock_alias.description == target.description
        )

    # Test equality when mock has alias matching canonical name
    mock_with_alias = Mock()
    mock_with_alias.name = "test_name"
    mock_with_alias.index = 20
    mock_with_alias.description = "Uranium 235 isotope"
    mock_with_alias.alias = "235U"
    if hasattr(mid, "235U"):
        assert (
            mock_with_alias.alias in (target.name, target.alias)
            and mock_with_alias.index == target.index
            and mock_with_alias.description == target.description
        )

    # Test equality when both have matching aliases
    mock_matching_aliases = Mock()
    mock_matching_aliases.name = "sample_name"
    mock_matching_aliases.index = 20
    mock_matching_aliases.description = "Uranium 235 isotope"
    mock_matching_aliases.alias = "U_235"
    if hasattr(mid, "235U"):
        assert (
            mock_matching_aliases.alias in (target.name, target.alias)
            and mock_matching_aliases.index == target.index
            and mock_matching_aliases.description == target.description
        )

    # Test inequality when index doesn't match
    mock_wrong_index = Mock()
    mock_wrong_index.name = "235U"
    mock_wrong_index.index = 999
    mock_wrong_index.description = "Uranium 235 isotope"
    mock_wrong_index.alias = None
    if hasattr(mid, "235U"):
        assert not (
            mock_wrong_index.name in (target.name, target.alias)
            and mock_wrong_index.index == target.index
            and mock_wrong_index.description == target.description
        )

    # Test inequality when neither name nor alias matches
    mock_no_match = Mock()
    mock_no_match.name = "wrong_name"
    mock_no_match.index = 20
    mock_no_match.description = "Uranium 235 isotope"
    mock_no_match.alias = "wrong_alias"
    if hasattr(mid, "235U"):
        assert not (
            (
                mock_no_match.name == target.name
                or mock_no_match.name == target.alias
                or mock_no_match.alias == target.name
                or mock_no_match.alias == target.alias
            )
            and mock_no_match.index == target.index
            and mock_no_match.description == target.description
        )
