import logging
import pprint
from copy import deepcopy

import pytest

from imas.ids_factory import IDSFactory
from imas.ids_struct_array import IDSStructArray


@pytest.fixture
def struct_array(fake_filled_toplevel) -> IDSStructArray:
    struct_array = fake_filled_toplevel.wavevector
    struct_array.resize(3)
    assert len(struct_array.value) == 3
    return struct_array


@pytest.mark.parametrize("keep", (True, False))
@pytest.mark.parametrize("target_len", (1, 3, 7))
def test_resize(keep, target_len, struct_array):
    pre_struct_array_len = len(struct_array)
    pre_struct_array = deepcopy(struct_array)
    n_comp_values = min(target_len, pre_struct_array_len)
    pre_values = [struct_array[ii] for ii in range(n_comp_values)]

    # Test if resize works for 3->1, 3->3, and 3->7
    struct_array.resize(target_len, keep=keep)

    # Test if internal data is the right length
    assert len(struct_array) == target_len

    # Test if internal data is explicitly new (keep = False) or
    # explicitly kept (keep = True)
    for ii in range(n_comp_values):
        if keep:
            assert (
                struct_array[ii] is pre_values[ii]
            ), f"On element {ii} of {struct_array.value} vs {pre_struct_array.value}"
        else:
            assert (
                struct_array[ii] is not pre_values[ii]
            ), f"On element {ii} of {struct_array.value} vs {pre_struct_array.value}"


def test_pretty_print(struct_array):
    assert (
        pprint.pformat(struct_array)
        == "<IDSStructArray (IDS:gyrokinetics, wavevector with 3 items)>"
    )


def test_path_non_indexable_parent(caplog, fake_filled_toplevel):
    top = fake_filled_toplevel
    top.wavevector.resize(1)
    wv = top.wavevector[0]
    with caplog.at_level(logging.WARNING):
        assert wv._path == "wavevector[0]"
        for record in caplog.records:
            assert record.levelname != "WARNING"

    # Remove the referenced profiles_1d from its parent
    top.wavevector.resize(0)

    # Check if singular warning is raised
    with caplog.at_level(logging.WARNING):
        assert wv._path == "wavevector[?]"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"


def test_struct_array_eq():
    cp1 = IDSFactory("3.39.0").core_profiles()
    cp2 = IDSFactory("3.39.0").core_profiles()

    assert cp1.profiles_1d != 1
    assert cp1.profiles_1d != "profiles_1d"

    assert cp1.profiles_1d == cp2.profiles_1d
    cp1.profiles_1d.resize(1)
    assert cp1.profiles_1d != cp2.profiles_1d
    cp2.profiles_1d.resize(2)
    assert cp1.profiles_1d != cp2.profiles_1d
    cp1.profiles_1d.resize(2)
    assert cp1.profiles_1d == cp2.profiles_1d
    cp1.profiles_1d[0].time = 1
    assert cp1.profiles_1d != cp2.profiles_1d
    cp2.profiles_1d[0].time = 1
    assert cp1.profiles_1d == cp2.profiles_1d
