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
