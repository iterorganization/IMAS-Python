# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
import pprint

import numpy as np

from imas.ids_primitive import IDSPrimitive
from imas.util import visit_children

# As the IDSPrimitive class generally should not be used on its own. Instead we
# take a very well defined toplevel, initialize it, and do our tests on the
# tree structure that is generated. Keep the tests just to the functionality
# that is defined in ids_primitive.py though!


zero_to_two_pi = np.linspace(0, 2, num=10) * np.pi


def test_pretty_print(fake_filled_toplevel):
    eig = fake_filled_toplevel.wavevector[0].eigenmode[0]
    assert pprint.pformat(fake_filled_toplevel).startswith("<IDSToplevel")
    assert pprint.pformat(fake_filled_toplevel.wavevector[0].eigenmode).startswith(
        "<IDSStructArray ("
    )
    assert pprint.pformat(fake_filled_toplevel.wavevector[0].eigenmode[0]).startswith(
        "<IDSStructure ("
    )
    assert pprint.pformat(eig.time_norm).startswith("<IDSNumericArray")
    assert pprint.pformat(eig.time_norm).endswith("empty FLT_1D)>")
    assert pprint.pformat(eig.frequency_norm).startswith("<IDSFloat0D")
    assert pprint.pformat(eig.frequency_norm).endswith("\nfloat(10.0)")
    fake_filled_toplevel.ids_properties.comment = "A filled comment"
    assert (
        pprint.pformat(fake_filled_toplevel.ids_properties.comment)
        == """<IDSString0D (IDS:gyrokinetics, ids_properties/comment, STR_0D)>
str('A filled comment')"""
    )


def test_value_attribute(fake_filled_toplevel):
    """Test if the value attribute acts as imas-python expects"""
    eig = fake_filled_toplevel.wavevector[0].eigenmode[0]
    assert isinstance(eig.frequency_norm, IDSPrimitive)
    assert hasattr(eig.frequency_norm, "value")

    # We should have a Python Primitive now:
    assert eig.frequency_norm.data_type == "FLT_0D"
    assert isinstance(eig.frequency_norm.value, float)
    assert eig.frequency_norm.value == 10

    # For arrays, we should get numpy arrays of the right type
    # This one should be not-filled, e.g. default
    assert not eig.phi_potential_perturbed_norm.has_value
    assert eig.phi_potential_perturbed_norm.data_type == "CPX_2D"
    assert isinstance(eig.phi_potential_perturbed_norm.value, np.ndarray)
    assert np.array_equal(eig.phi_potential_perturbed_norm.value, np.ndarray((0, 0)))

    # Finally, check a filled array
    assert eig.poloidal_angle.has_value
    assert eig.poloidal_angle.data_type == "FLT_1D"
    assert isinstance(eig.poloidal_angle.value, np.ndarray)
    assert np.array_equal(eig.poloidal_angle.value, zero_to_two_pi)


def test_visit_children(fake_filled_toplevel):
    # This should visit leaf nodes only. Lets test that, but check only
    # filled fields explicitly
    nodes = []

    def append_if_has_value(xx):
        if xx.has_value:
            nodes.append(xx)

    visit_children(append_if_has_value, fake_filled_toplevel)
    assert len(nodes) == 3
    assert nodes[0] == 2
    assert nodes[1] == 10
    assert np.array_equal(nodes[2], zero_to_two_pi)


def test_visit_children_internal_nodes(fake_filled_toplevel):
    nodes = []

    def append_if_has_value(xx):
        if xx.has_value:
            nodes.append(xx)

    visit_children(append_if_has_value, fake_filled_toplevel, leaf_only=False)
    # We now visit the internal nodes too.

    # We know we filled only endpoints frequency_norm and poloidal_angle
    # We expect the following "mandatory" fields to be touched, which we check
    # in the order visit_children visits
    assert len(nodes) == 9
    assert nodes[0] is fake_filled_toplevel
    assert nodes[1] is fake_filled_toplevel.ids_properties
    assert nodes[2] == 2
    assert nodes[3] is fake_filled_toplevel.wavevector
    assert nodes[4] is fake_filled_toplevel.wavevector[0]
    assert nodes[5] is fake_filled_toplevel.wavevector[0].eigenmode
    assert nodes[6] is fake_filled_toplevel.wavevector[0].eigenmode[0]
    assert nodes[7] == 10
    assert np.array_equal(nodes[8], zero_to_two_pi)


def test_assign_nan(fake_filled_toplevel, caplog):
    with caplog.at_level("DEBUG"):
        fake_filled_toplevel.wavevector[0].radial_component_norm = float("nan")
    assert len(caplog.records) == 0
