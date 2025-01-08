# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
import copy
import pprint

import pytest

from imas.ids_factory import IDSFactory
from imas.ids_structure import IDSStructure


@pytest.fixture
def structure(fake_filled_toplevel) -> IDSStructure:
    yield fake_filled_toplevel.ids_properties


def test_pretty_print(structure):
    assert (
        pprint.pformat(structure) == "<IDSStructure (IDS:gyrokinetics, ids_properties)>"
    )


def test_dict_like_access(fake_filled_toplevel):
    assert fake_filled_toplevel["ids_properties"] is fake_filled_toplevel.ids_properties
    node = fake_filled_toplevel.ids_properties.provenance.node
    assert fake_filled_toplevel["ids_properties/provenance/node"] is node
    node.resize(1)
    assert fake_filled_toplevel["ids_properties/provenance/node[0]"] is node[0]
    assert fake_filled_toplevel["ids_properties/provenance/node[0]"] is node[0]
    path = node[0].path
    assert fake_filled_toplevel["ids_properties/provenance/node[0]/path"] is path


def test_dict_like_setitem():
    cp = IDSFactory("3.39.0").core_profiles()

    cp["time"] = [1, 2, 3]
    assert cp.time[0] == 1, cp.time[2] == 3

    cp["ids_properties/homogeneous_time"] = 1
    assert cp.ids_properties.homogeneous_time == 1

    provenance_copy = copy.deepcopy(cp.ids_properties.provenance)
    provenance_copy.node.resize(1)
    provenance_copy.node[0].path = "test"
    cp["ids_properties/provenance/node"] = provenance_copy.node


def test_structure_eq():
    cp1 = IDSFactory("3.39.0").core_profiles()
    cp2 = IDSFactory("3.39.0").core_profiles()

    assert cp1 != 1
    assert cp1 != "1"
    assert cp1 != cp1.time

    assert cp1 == cp2
    assert cp1.ids_properties == cp2.ids_properties
    cp1.ids_properties.comment = "x"
    assert cp1 != cp2
    assert cp1.ids_properties != cp2.ids_properties
    cp2.ids_properties.comment = "x"
    assert cp1 == cp2
    assert cp1.ids_properties == cp2.ids_properties
    cp2.ids_properties.homogeneous_time = 1
    assert cp1 != cp2
    assert cp1.ids_properties != cp2.ids_properties
    cp1.ids_properties.homogeneous_time = 1
    assert cp1 == cp2
    assert cp1.ids_properties == cp2.ids_properties
