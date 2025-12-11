import pytest

import imas.training
from imas.util import idsdiffgen
from imas.test.test_helpers import fill_with_random_data


def assert_equal(core_edge, plasma):
    # We only expect the IDS name to be different:
    difflist = list(idsdiffgen(core_edge, plasma))
    assert difflist == [("IDS name", core_edge.metadata.name, plasma.metadata.name)]


def test_convert_training_core_profiles():
    with imas.training.get_training_db_entry() as entry:
        cp = entry.get("core_profiles")

    pp = imas.convert_to_plasma_profiles(cp)
    assert_equal(cp, pp)


def test_convert_missing_qty():
    cp = imas.IDSFactory("4.1.0").core_profiles()
    cp.profiles_1d.resize(1)
    cp.profiles_1d[0].ion.resize(1)
    cp.profiles_1d[0].ion[0].state.resize(1)
    cp.profiles_1d[0].ion[0].state[0].ionization_potential = 0.5

    pp = imas.convert_to_plasma_profiles(cp)
    # check that state[0] is copied, but that it's empty
    assert not pp.profiles_1d[0].ion[0].state[0].has_value


@pytest.mark.parametrize("idsname", ["core_profiles", "edge_profiles"])
def test_convert_randomly_filled_profiles(idsname):
    ids = imas.IDSFactory("4.1.0").new(idsname)
    fill_with_random_data(ids)

    if idsname == "core_profiles":
        # ionization_potential doesn't exist in plasma_profiles in DD 4.1.0. This case
        # is tested in test_convert_missing_qty. Unset these variables to avoid a diff:
        for profiles in list(ids.profiles_1d) + list(ids.profiles_2d):
            for ion in profiles.ion:
                for state in ion.state:
                    del state.ionization_potential
                    del state.ionization_potential_error_upper
                    del state.ionization_potential_error_lower

    plasma = imas.convert_to_plasma_profiles(ids)
    assert_equal(ids, plasma)


@pytest.mark.parametrize("idsname", ["core_sources", "edge_sources"])
def test_convert_randomly_filled_sources(idsname):
    ids = imas.IDSFactory("4.1.0").new(idsname)
    fill_with_random_data(ids)

    plasma = imas.convert_to_plasma_sources(ids)
    assert_equal(ids, plasma)


@pytest.mark.parametrize("idsname", ["core_transport", "edge_transport"])
def test_convert_randomly_filled_transport(idsname):
    ids = imas.IDSFactory("4.1.0").new(idsname)
    fill_with_random_data(ids)

    plasma = imas.convert_to_plasma_transport(ids)
    assert_equal(ids, plasma)
