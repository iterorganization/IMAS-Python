import importlib.metadata
from packaging.version import Version

import pytest
from imas.dd_zip import dd_identifiers
from imas.ids_factory import IDSFactory
from imas.ids_identifiers import IDSIdentifier, identifiers

has_aliases = Version(importlib.metadata.version("imas_data_dictionaries")) >= Version(
    "4.1.0"
)
requires_aliases = pytest.mark.skipif(
    not has_aliases, reason="Requires DD 4.1.0 for identifier aliases"
)


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


def test_identifiers_with_aliases():
    # Custom identifier XML, based on materials identifier, with some more features
    custom_identifier_xml = """\
<?xml version="1.0"?>
<constants name="materials" identifier="yes" create_mapping_function="yes">
<header>
Materials used in the device mechanical structures
</header>
<int name="235U" alias="U_235" description="Uranium 235 isotope">20</int>
<int name="238U" alias="U_238" description="Uranium 238 isotope">21</int>
<int name="Diamond" description="Diamond">22</int>
<int name="CxHy" alias="alias1,alias2,3alias" description="Organic molecule">23</int>
</constants>
"""
    identifier = IDSIdentifier._from_xml("custom_identifier", custom_identifier_xml)

    assert len(identifier) == 4

    # no aliases
    assert identifier.Diamond.aliases == []
    # 1 alias
    assert identifier["235U"] is identifier.U_235
    assert identifier["235U"].aliases == ["U_235"]
    # 3 aliases
    assert (
        identifier.CxHy
        is identifier.alias1
        is identifier.alias2
        is identifier["3alias"]
    )
    assert identifier.CxHy.aliases == ["alias1", "alias2", "3alias"]


@requires_aliases
def test_identifier_struct_assignment_with_aliases():
    """Test identifier struct assignment with aliases using materials_identifier."""
    mid = identifiers.materials_identifier

    # Create an actual IDS structure
    wallids = IDSFactory().wall()
    wallids.description_ggd.resize(1)
    wallids.description_ggd[0].material.resize(1)
    wallids.description_ggd[0].material[0].grid_subset.resize(1)
    mat = wallids.description_ggd[0].material[0].grid_subset[0].identifiers
    mat.names.extend([""] * 1)
    mat.indices.resize(1)
    mat.descriptions.extend([""] * 1)
    mat.names[0] = mid.U_235.name
    mat.indices[0] = 20
    mat.descriptions[0] = "Uranium 235 isotope"

    # Basic attribute checks
    assert mat.names[0] == mid["235U"].name
    assert mat.indices[0] == mid.U_235.index

    # Modify material properties and test equality
    mat.names[0] = "some_name"
    assert mat.names[0] != mid.U_235.name


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


@requires_aliases
def test_identifier_aliases():
    """Test identifier enum aliases functionality."""
    mid = identifiers.materials_identifier

    # Test that alias points to the same object as the canonical name
    assert mid.U_235 is mid["235U"]
    assert mid.U_238 is mid["238U"]
    assert mid.In_115 is mid["115In"]
    assert mid.He_4 is mid["4He"]

    # Test that both name and alias have the same properties
    assert mid.U_235.name == "235U"
    assert mid.U_235.index == mid["235U"].index
    assert mid.U_235.description == mid["235U"].description
    assert "U_235" in mid.U_235.aliases
    assert isinstance(mid.U_235.aliases, list)

    # Test accessing by any alias via bracket notation
    for alias in mid.U_235.aliases:
        assert mid[alias] is mid.U_235


@requires_aliases
def test_identifier_alias_equality():
    """Test that identifiers with aliases are equal when comparing names and aliases."""
    mid = identifiers.materials_identifier
    target = mid.U_235

    # Test equality with canonical name
    wallids = IDSFactory().wall()
    wallids.description_ggd.resize(1)
    wallids.description_ggd[0].material.resize(1)
    wallids.description_ggd[0].material[0].grid_subset.resize(1)
    mat = wallids.description_ggd[0].material[0].grid_subset[0].identifiers
    mat.names.extend([""] * 1)
    mat.names[0] = "235U"
    assert mat.names[0] == target.name

    # Test equality with alias name
    wallids2 = IDSFactory().wall()
    wallids2.description_ggd.resize(1)
    wallids2.description_ggd[0].material.resize(1)
    wallids2.description_ggd[0].material[0].grid_subset.resize(1)
    mat2 = wallids2.description_ggd[0].material[0].grid_subset[0].identifiers
    mat2.names.extend([""] * 1)
    mat2.names[0] = mid["U_235"].name  # Use alias as name
    assert mat2.names[0] == target.name

    # Test inequality when material has alias not matching canonical name
    wallids3 = IDSFactory().wall()
    wallids3.description_ggd.resize(1)
    wallids3.description_ggd[0].material.resize(1)
    wallids3.description_ggd[0].material[0].grid_subset.resize(1)
    mat3 = wallids3.description_ggd[0].material[0].grid_subset[0].identifiers
    mat3.names.extend([""] * 1)
    mat3.names[0] = "test_name"
    assert mat3.names[0] != target.name

    # Test equality when index doesn't match
    wallids4 = IDSFactory().wall()
    wallids4.description_ggd.resize(1)
    wallids4.description_ggd[0].material.resize(1)
    wallids4.description_ggd[0].material[0].grid_subset.resize(1)
    mat4 = wallids4.description_ggd[0].material[0].grid_subset[0].identifiers
    mat4.names.extend([""] * 1)
    mat4.indices.resize(1)
    mat4.names[0] = "235U"
    mat4.indices[0] = 999
    assert mat4.indices[0] != target.index
    assert mat4.names[0] == target.name

    # Test equality for multiple names,indices and descriptions
    wallids5 = IDSFactory().wall()
    wallids5.description_ggd.resize(1)
    wallids5.description_ggd[0].material.resize(1)
    wallids5.description_ggd[0].material[0].grid_subset.resize(1)
    mat5 = wallids5.description_ggd[0].material[0].grid_subset[0].identifiers
    mat5.names.extend([""] * 3)
    mat5.indices.resize(3)
    mat5.descriptions.extend([""] * 3)
    mat5.names[0] = "235U"
    mat5.names[1] = "238U"
    mat5.names[2] = mid.U_235.name  # Use alias as name
    mat5.indices[0] = 20
    mat5.indices[1] = 21
    mat5.indices[2] = 20
    mat5.descriptions[0] = "Uranium 235 isotope"
    mat5.descriptions[1] = "Uranium 238 isotope"
    mat5.descriptions[2] = "Uranium 235 isotope"

    assert mat5.names[0] == mid["235U"].name
    assert mat5.names[1] == mid["238U"].name
    assert mat5.names[2] == mid["U_235"].name
    assert mat5.indices[0] == mid["235U"].index
    assert mat5.indices[1] == mid["238U"].index
    assert mat5.indices[2] == mid["U_235"].index
    assert mat5.descriptions[0] == mid["235U"].description
    assert mat5.descriptions[1] == mid["238U"].description
    assert mat5.descriptions[2] == mid["U_235"].description


@requires_aliases
def test_identifier_alias_equality_non_ggd():
    """Test identifier aliases functionality on non-ggd material"""
    mid = identifiers.materials_identifier

    summary_ids = IDSFactory().summary()
    summary_ids.wall.material = mid.U_235  # Use alias as enum
    assert summary_ids.wall.material == mid["235U"]
    assert summary_ids.wall.material == mid["U_235"]

    summary_ids.wall.material.name = "U_235"  # Use alias as name
    assert summary_ids.wall.material == mid["235U"]
    assert summary_ids.wall.material == mid["U_235"]

    summary_ids.wall.material.name = "235U"  # Use canonical name
    assert summary_ids.wall.material == mid["235U"]
    assert summary_ids.wall.material == mid["U_235"]
