import copy

import imas
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure
from imas.test.test_helpers import compare_children, fill_with_random_data


def validate_parent(node):
    for child in node:
        assert child._parent is node
        if isinstance(child, (IDSStructure, IDSStructArray)):
            validate_parent(child)


def test_deepcopy():
    factory = imas.IDSFactory()
    cp = factory.core_profiles()
    fill_with_random_data(cp)

    cp2 = copy.deepcopy(cp)
    compare_children(cp, cp2)

    validate_parent(cp)
    validate_parent(cp2)
