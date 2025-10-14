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
    factory = IDSFactory("4.0.0").camera_x_rays()
    mat = factory.filter_window.material
    mat.name = "235U"
    mat.index = 20
    mat.description = "Uranium 235 isotope"
    mat.alias = "U_235"

    # Basic attribute checks
    assert mat.name == mid["235U"].name
    assert mat.alias == mid.U_235.alias
    assert mat.index == mid.U_235.index

    # Test various equality scenarios
    assert mat == mid.U_235
    assert mat == mid["235U"]

    # Modify material properties and test equality
    mat.name = "some_name"
    mat.alias = "U_235"
    assert mat == mid.U_235

    mat.alias = "235U"
    assert mat == mid.U_235


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
    assert mid.U_235.alias == "U_235"

    # Test accessing by alias via bracket notation
    assert mid["U_235"] is mid.U_235
    assert mid["U_238"] is mid.U_238
    assert mid["In_115"] is mid.In_115
    assert mid["He_4"] is mid.He_4


@requires_aliases
def test_identifier_alias_equality():
    """Test that identifiers with aliases are equal when comparing names and aliases."""
    mid = identifiers.materials_identifier
    target = mid.U_235

    # Test equality with canonical name
    factory1 = IDSFactory("4.0.0").camera_x_rays()
    mat1 = factory1.filter_window.material
    mat1.name = "235U"
    mat1.index = 20
    mat1.description = "Uranium 235 isotope"
    assert mat1 == target

    # Test equality with alias name
    factory2 = IDSFactory("4.0.0").camera_x_rays()
    mat2 = factory2.filter_window.material
    mat2.name = "U_235"
    mat2.index = 20
    mat2.description = "Uranium 235 isotope"
    assert mat2 == target

    # Test equality when material has alias matching canonical name
    factory3 = IDSFactory("4.0.0").camera_x_rays()
    mat3 = factory3.filter_window.material
    mat3.name = "test_name"
    mat3.index = 20
    mat3.description = "Uranium 235 isotope"
    mat3.alias = "235U"
    assert mat3 == target

    # Test inequality when index doesn't match
    factory4 = IDSFactory("4.0.0").camera_x_rays()
    mat4 = factory4.filter_window.material
    mat4.name = "235U"
    mat4.index = 999
    mat4.description = "Uranium 235 isotope"
    assert mat4 != target

    # Test inequality when neither name nor alias matches
    factory5 = IDSFactory("4.0.0").camera_x_rays()
    mat5 = factory5.filter_window.material
    mat5.name = "wrong_name"
    mat5.index = 20
    mat5.description = "Uranium 235 isotope"
    mat5.alias = "wrong_alias"
    assert mat5 != target

    # Test equality with material having alias matching canonical name
    factory6 = IDSFactory("4.0.0").camera_x_rays()
    mat6 = factory6.filter_window.material
    mat6.name = "test_name"
    mat6.index = 20
    mat6.description = "Uranium 235 isotope"
    mat6.alias = "235U"
    assert mat6 == target

    # Test equality when both have matching aliases
    factory7 = IDSFactory("4.0.0").camera_x_rays()
    mat7 = factory7.filter_window.material
    mat7.name = "sample_name"
    mat7.index = 20
    mat7.description = "Uranium 235 isotope"
    mat7.alias = "U_235"
    assert mat7 == target

    # Test inequality when index doesn't match
    factory8 = IDSFactory("4.0.0").camera_x_rays()
    mat8 = factory8.filter_window.material
    mat8.name = "235U"
    mat8.index = 999
    mat8.description = "Uranium 235 isotope"
    assert mat8 != target

    # Test inequality when neither name nor alias matches
    factory9 = IDSFactory("4.0.0").camera_x_rays()
    mat9 = factory9.filter_window.material
    mat9.name = "wrong_name"
    mat9.index = 20
    mat9.description = "Uranium 235 isotope"
    mat9.alias = "wrong_alias"
    assert mat9 != target

    # Test equality when material has list of multiple aliases
    factory10 = IDSFactory("4.0.0").camera_x_rays()
    mat10 = factory10.filter_window.material
    mat10.name = "test_name"
    mat10.index = 20
    mat10.description = "Uranium 235 isotope"
    mat10.alias = "235U,U_235,Uranium_235"
    assert mat10 == target
    assert mat10.alias[0] == target[0]
    assert mat10.alias[1] == target[0]
    assert mat10.alias[2] == target[0]
    assert mat10.alias[1] == target[2]
    assert mat10.alias[2] == target[1]

    # Test equality when material has multiple aliases
    factory11 = IDSFactory("4.0.0").camera_x_rays()
    mat0 = factory11.filter_window.material
    mat0.name = "test_name"
    mat0.index = 20
    mat0.description = "Uranium 235 isotope"
    mat0.alias = "U_235"

    mat1 = factory11.filter_window.material
    mat1.name = "test_name"
    mat1.index = 20
    mat1.description = "Uranium 235 isotope"
    mat1.alias = "Uranium_235"
    assert mat0 == mat1 == target
