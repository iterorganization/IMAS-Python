import pytest

import imas
from imas.backends.imas_core.imas_interface import ll_interface


def test_catch_al_exception(requires_imas):
    # Do something which lets the lowlevel Cython interface throw an ALException
    # Ensure we can catch it:
    with pytest.raises(imas.exception.ALException):
        # Try to write an unknown data type (object)
        ll_interface.write_data(-1, "X", "", object())
