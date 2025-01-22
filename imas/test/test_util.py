import pytest

import imas
from imas.db_entry import DBEntry
from imas.ids_defs import MEMORY_BACKEND
from imas.test.test_helpers import fill_consistent
from imas.training import get_training_db_entry
from imas.util import (
    find_paths,
    get_data_dictionary_version,
    get_full_path,
    get_parent,
    get_time_mode,
    get_toplevel,
    idsdiffgen,
    inspect,
    is_lazy_loaded,
    print_metadata_tree,
    print_tree,
    tree_iter,
)


def test_tree_iter():
    cp = imas.IDSFactory("3.39.0").new("core_profiles")

    # Test tree iterator over empty IDS
    assert list(tree_iter(cp)) == []
    assert list(tree_iter(cp, leaf_only=False)) == []
    assert list(tree_iter(cp, leaf_only=False, include_node=True)) == [cp]

    # Fill some data and test again
    cp.ids_properties.homogeneous_time = 1
    ht = cp.ids_properties.homogeneous_time
    assert list(tree_iter(cp)) == [ht]
    assert list(tree_iter(cp, leaf_only=False)) == [cp.ids_properties, ht]
    expected = [cp, cp.ids_properties, ht]
    assert list(tree_iter(cp, leaf_only=False, include_node=True)) == expected

    # Test if empty values are iterated over as expected
    visit_empty = list(tree_iter(cp.ids_properties, visit_empty=True))
    ip = cp.ids_properties
    assert visit_empty[:4] == [ip.comment, ht, ip.source, ip.provider]


def test_inspect():
    cp = imas.IDSFactory("3.39.0").new("core_profiles")
    inspect(cp)  # IDSToplevel
    inspect(cp.ids_properties)  # IDSStructure
    cp.profiles_1d.resize(5)
    inspect(cp.profiles_1d)  # IDSStructArray
    inspect(cp.profiles_1d[1])  # IDSStructure inside array
    inspect(cp.profiles_1d[1].grid)  # IDSStructure inside array
    inspect(cp.profiles_1d[1].grid.rho_tor_norm)  # IDSPrimitive


def test_inspect_lazy():
    with get_training_db_entry() as entry:
        cp = entry.get("core_profiles", lazy=True)
        inspect(cp)


def test_print_tree():
    cp = imas.IDSFactory("3.39.0").new("core_profiles")
    fill_consistent(cp)
    print_tree(cp)  # Full IDS tree
    print_tree(cp.ids_properties)  # Sub-tree


def test_print_metadata_tree():
    cp = imas.IDSFactory("3.39.0").new("core_profiles")
    print_metadata_tree(cp, 1)
    print_metadata_tree(cp.metadata, 1)
    print_metadata_tree(cp.metadata["ids_properties"], 0)
    print_metadata_tree(cp.metadata["profiles_1d/electrons"])


def test_find_paths():
    cp = imas.IDSFactory("3.39.0").new("core_profiles")
    matches = find_paths(cp, "(^|/)time$")
    assert matches == ["profiles_1d/time", "profiles_2d/time", "time"]


def test_idsdiffgen():
    factory1 = imas.IDSFactory("3.39.0")
    factory2 = imas.IDSFactory("3.32.0")
    cp1 = factory1.new("core_profiles")
    cp2 = factory2.new("core_profiles")
    eq1 = factory1.new("equilibrium")

    # Test different DD versions
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0][1:] == ("3.39.0", "3.32.0")

    # Test different IDSs
    diff = list(idsdiffgen(cp1, eq1))
    assert len(diff) == 1
    assert diff[0][1:] == ("core_profiles", "equilibrium")

    cp2 = factory1.new("core_profiles")
    # Test different structures
    cp2.ids_properties.homogeneous_time = 1
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0] == ("ids_properties/homogeneous_time", None, 1)

    # Test different values
    cp1.ids_properties.homogeneous_time = 2
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0] == ("ids_properties/homogeneous_time", 2, 1)

    cp1.ids_properties.homogeneous_time = 1
    # Test missing values
    cp1.time = [1.0, 2.0]
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0] == ("time", cp1.time, None)

    # Test different array values
    cp2.time = [2.0, 1.0]
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0] == ("time", cp1.time, cp2.time)

    cp2.time = cp1.time
    # Test different AoS lengths
    cp1.profiles_1d.resize(1)
    cp2.profiles_1d.resize(2)
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0] == ("profiles_1d", cp1.profiles_1d, cp2.profiles_1d)

    # Test different values inside AoS
    cp2.profiles_1d.resize(1)
    cp1.profiles_1d[0].time = -1
    cp2.profiles_1d[0].time = 0
    diff = list(idsdiffgen(cp1, cp2))
    assert len(diff) == 1
    assert diff[0] == ("profiles_1d/time", -1, 0)


def test_idsdiff():
    # Test the diff rendering for two sample IDSs
    with get_training_db_entry() as entry:
        imas.util.idsdiff(entry.get("core_profiles"), entry.get("equilibrium"))


def test_get_parent():
    cp = imas.IDSFactory("3.39.0").core_profiles()
    cp.profiles_1d.resize(2)
    assert (
        get_parent(cp.profiles_1d[0].electrons.temperature)
        is cp.profiles_1d[0].electrons
    )
    assert get_parent(cp.profiles_1d[0].electrons) is cp.profiles_1d[0]
    assert get_parent(cp.profiles_1d[0]) is cp.profiles_1d
    assert get_parent(cp.profiles_1d) is cp
    assert get_parent(cp) is None


def test_get_time_mode():
    cp = imas.IDSFactory("3.39.0").core_profiles()
    cp.profiles_1d.resize(2)
    assert (
        get_time_mode(cp.profiles_1d[0].electrons.temperature)
        is cp.ids_properties.homogeneous_time
    )


def test_get_toplevel():
    cp = imas.IDSFactory("3.39.0").core_profiles()
    cp.profiles_1d.resize(2)
    assert get_toplevel(cp.profiles_1d[0].electrons.temperature) is cp
    assert get_toplevel(cp.profiles_1d[0].electrons) is cp
    assert get_toplevel(cp.profiles_1d[0]) is cp
    assert get_toplevel(cp.profiles_1d) is cp
    assert get_toplevel(cp) is cp


def test_is_lazy_loaded():
    with get_training_db_entry() as entry:
        assert is_lazy_loaded(entry.get("core_profiles")) is False
        assert is_lazy_loaded(entry.get("core_profiles", lazy=True)) is True


def test_get_full_path():
    cp = imas.IDSFactory("3.39.0").core_profiles()
    cp.profiles_1d.resize(2)
    assert (
        get_full_path(cp.profiles_1d[1].electrons.temperature)
        == "profiles_1d[1]/electrons/temperature"
    )


@pytest.mark.parametrize("version", ["3.31.0", "3.39.0"])
def test_get_dd_version(version):
    entry = DBEntry(MEMORY_BACKEND, "test", 0, 0, dd_version=version)
    assert get_data_dictionary_version(entry) == version
    assert get_data_dictionary_version(entry.factory) == version

    cp = entry.factory.core_profiles()
    cp.profiles_1d.resize(2)
    assert get_data_dictionary_version(cp.profiles_1d[0].electrons) == version
    assert get_data_dictionary_version(cp.profiles_1d[0]) == version
    assert get_data_dictionary_version(cp.profiles_1d) == version
    assert get_data_dictionary_version(cp) == version
    assert get_data_dictionary_version(cp.time) == version
