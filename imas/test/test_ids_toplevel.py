"""A testcase checking higher-level IDSToplevel features with a fake
constant-in-time DD
"""

import pprint
from pathlib import Path

import pytest

from imas.ids_factory import IDSFactory
from imas.ids_toplevel import IDSToplevel
from imas.test.test_helpers import compare_children, fill_with_random_data


@pytest.fixture
def ids(fake_toplevel_xml: Path):
    return IDSFactory(xml_path=fake_toplevel_xml).new("gyrokinetics")


def test_toplevel_init(ids):
    assert isinstance(ids, IDSToplevel)


def test_structure_xml_noncopy(ids):
    assert id(list(ids.metadata._structure_xml)[0].attrib) == id(
        ids.ids_properties.metadata._structure_xml.attrib
    )


def test_metadata_lifecycle_status(ids):
    assert ids.metadata.lifecycle_status == "alpha"
    assert ids.wavevector.metadata.structure_reference == "gyrokinetics_wavevector"


def test_metadata_non_exist(ids):
    with pytest.raises(AttributeError):
        ids.wavevector.metadata.lifecycle_status


def test_metadata_attribute_not_exists(ids):
    with pytest.raises(AttributeError):
        ids.metadata.blergh


def test_pretty_print(ids):
    assert pprint.pformat(ids) == "<IDSToplevel (IDS:gyrokinetics)>"


def test_serialize_nondefault_dd_version():
    ids = IDSFactory("3.31.0").core_profiles()
    fill_with_random_data(ids)
    data = ids.serialize()
    ids2 = IDSFactory("3.31.0").core_profiles()
    ids2.deserialize(data)
    compare_children(ids, ids2)
