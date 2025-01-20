# This file is part of IMASPy.
# You should have received the IMASPy LICENSE file with this project.
import pytest
from imaspy.backends.imas_core.imas_interface import has_imas


@pytest.mark.skipif(has_imas, reason="Requires IMAS Core.")
def test_toplevel(fake_filled_toplevel):
    top = fake_filled_toplevel
    assert top.wavevector._toplevel == top
    assert top.wavevector[0].radial_component_norm._toplevel == top


def test_path(fake_filled_toplevel):
    top = fake_filled_toplevel
    assert top.wavevector._path == "wavevector"
    assert top.ids_properties.creation_date._path == "ids_properties/creation_date"
    assert top.wavevector._path == "wavevector"
    assert top.wavevector[0]._path == "wavevector[0]"
    assert (
        top.wavevector[0].radial_component_norm._path
        == "wavevector[0]/radial_component_norm"
    )
