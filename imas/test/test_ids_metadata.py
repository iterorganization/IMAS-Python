from copy import deepcopy

import pytest

from imas.ids_factory import IDSFactory
from imas.ids_metadata import IDSType, get_toplevel_metadata


def test_metadata_cache(fake_structure_xml):
    meta = get_toplevel_metadata(fake_structure_xml)
    meta2 = get_toplevel_metadata(fake_structure_xml)
    assert meta is meta2


def test_metadata_init_structure_xml(fake_structure_xml):
    meta = get_toplevel_metadata(fake_structure_xml)
    assert fake_structure_xml.attrib["name"] == "gyrokinetics"
    assert meta.name == "gyrokinetics"


def test_metadata_deepcopy(fake_structure_xml):
    meta = get_toplevel_metadata(fake_structure_xml)
    meta2 = deepcopy(meta)

    # Test that deepcopy returns the same reference
    assert meta is meta2
    assert meta == meta2


def test_metadata_immutable(fake_structure_xml):
    meta = get_toplevel_metadata(fake_structure_xml)
    with pytest.raises(RuntimeError):
        meta.immutable = True
    with pytest.raises(RuntimeError):
        del meta.name


def test_ids_type():
    assert not IDSType.NONE.is_dynamic
    assert not IDSType.CONSTANT.is_dynamic
    assert not IDSType.STATIC.is_dynamic
    assert IDSType.DYNAMIC.is_dynamic


def test_metadata_indexing():
    core_profiles = IDSFactory("3.39.0").core_profiles()
    metadata = core_profiles.metadata
    assert metadata["ids_properties"] is core_profiles.ids_properties.metadata
    assert (
        metadata["ids_properties/version_put"]
        is core_profiles.ids_properties.version_put.metadata
    )
    assert metadata["time"] is core_profiles.time.metadata
    p1d_time_meta = metadata["profiles_1d/time"]
    core_profiles.profiles_1d.resize(1)
    assert p1d_time_meta is core_profiles.profiles_1d[0].time.metadata

    # Test period (.) as separator:
    assert (
        metadata["profiles_1d/electrons/temperature"]
        is metadata["profiles_1d.electrons.temperature"]
    )

    # Test invalid path
    with pytest.raises(KeyError):
        metadata["DoesNotExist"]
