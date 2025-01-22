import random
from unittest.mock import DEFAULT, patch

import numpy
import pytest

from imas.backends.imas_core.imas_interface import ll_interface
from imas.db_entry import DBEntry
from imas.ids_defs import (
    ASCII_BACKEND,
    IDS_TIME_MODE_HETEROGENEOUS,
    IDS_TIME_MODE_HOMOGENEOUS,
    MEMORY_BACKEND,
    PREVIOUS_INTERP,
)
from imas.ids_factory import IDSFactory
from imas.ids_primitive import IDSPrimitive
from imas.test.test_helpers import compare_children, fill_consistent, open_dbentry


def test_lazy_load_aos(backend, worker_id, tmp_path, log_lowlevel_calls):
    if backend == ASCII_BACKEND:
        pytest.skip("Lazy loading is not supported by the ASCII backend.")
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.39.0")
    ids = dbentry.factory.new("core_profiles")
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    ids.profiles_1d.resize(10)
    for i in range(10):
        ids.profiles_1d[i].time = i
    dbentry.put(ids)

    # Test a random access pattern of the AOS elements
    lazy_ids = dbentry.get("core_profiles", lazy=True)
    random_list = list(range(10))
    random.shuffle(random_list)
    for i in random_list:
        assert lazy_ids.profiles_1d[i].time == i
    # Now all profiles_1d/time are loaded, check that we use loaded values and do not
    # read data from the lowlevel
    to_patch = {"read_data": DEFAULT, "begin_arraystruct_action": DEFAULT}
    with patch.multiple(ll_interface, **to_patch) as values:
        assert len(lazy_ids.profiles_1d) == 10
        for i in range(10):
            assert lazy_ids.profiles_1d[i].time == i
        for method in to_patch:
            assert values[method].call_count == 0

    # Test get_slice
    lazy_ids_slice = dbentry.get_slice("core_profiles", 3.5, PREVIOUS_INTERP, lazy=True)
    assert lazy_ids_slice.profiles_1d.shape == (1,)
    assert lazy_ids_slice.profiles_1d[0].time == 3

    dbentry.close()


def test_lazy_loading_distributions_random(backend, worker_id, tmp_path):
    if backend == ASCII_BACKEND:
        pytest.skip("Lazy loading is not supported by the ASCII backend.")
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    ids = IDSFactory().new("distributions")
    fill_consistent(ids)
    dbentry.put(ids)

    def iterate(structure):
        for child in structure:
            if not isinstance(child, IDSPrimitive):
                iterate(child)

    lazy_ids = dbentry.get("distributions", lazy=True)
    # Iterate over whole IDS to force-load everything
    iterate(lazy_ids)
    compare_children(ids, lazy_ids, accept_lazy=True)

    dbentry.close()


def test_lazy_load_close_dbentry(requires_imas):
    dbentry = DBEntry(MEMORY_BACKEND, "ITER", 1, 1)
    dbentry.create()

    ids = dbentry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    dbentry.put(ids)

    lazy_ids = dbentry.get("core_profiles", lazy=True)
    dbentry.close()

    with pytest.raises(RuntimeError):
        print(lazy_ids.time)


def test_lazy_load_readonly(requires_imas):
    dbentry = DBEntry(MEMORY_BACKEND, "ITER", 1, 1)
    dbentry.create()

    ids = dbentry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    ids.time = [1, 2]
    dbentry.put(ids)

    lazy_ids = dbentry.get("core_profiles", lazy=True)
    assert lazy_ids._lazy is True

    # AoS modifiers
    with pytest.raises(ValueError):
        lazy_ids.profiles_1d.resize(1)
    with pytest.raises(ValueError):
        lazy_ids.profiles_1d.append(lazy_ids.profiles_1d._element_structure)
    with pytest.raises(ValueError):
        lazy_ids.profiles_1d[0] = None

    # Set IDSPrimitive
    with pytest.raises(ValueError):
        lazy_ids.ids_properties.homogeneous_time = 1
    with pytest.raises(ValueError):
        lazy_ids.time = [1, 2]
    # Modify numpy arrays
    with pytest.raises(ValueError):
        lazy_ids.time.resize(3)
    with pytest.raises(ValueError):
        lazy_ids.time.value[0] = 10

    dbentry.close()


def test_lazy_load_no_put(requires_imas):
    dbentry = DBEntry(MEMORY_BACKEND, "ITER", 1, 1)
    dbentry.create()

    ids = dbentry.factory.core_profiles()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    dbentry.put(ids)

    lazy_ids = dbentry.get("core_profiles", lazy=True)

    with pytest.raises(ValueError):
        dbentry.put(lazy_ids)
    with pytest.raises(ValueError):
        dbentry.put_slice(lazy_ids)

    dbentry.close()


def test_lazy_load_with_new_aos(requires_imas):
    dbentry = DBEntry(MEMORY_BACKEND, "ITER", 1, 1, dd_version="3.30.0")
    dbentry.create()
    et = dbentry.factory.edge_transport()

    et.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    et.time = [1.0]
    et.model.resize(1)
    et.model[0].ggd.resize(1)
    et.model[0].ggd[0].electrons.particles.d.resize(1)
    et.model[0].ggd[0].electrons.particles.d[0].grid_index = -1
    dbentry.put(et)

    entry2 = DBEntry(MEMORY_BACKEND, "ITER", 1, 1, dd_version="3.39.0")
    entry2.open()
    lazy_et = entry2.get("edge_transport", lazy=True)
    assert numpy.array_equal(lazy_et.time, [1.0])
    assert lazy_et.model[0].ggd[0].electrons.particles.d[0].grid_index == -1
    # d_radial did not exist in 3.30.0
    assert len(lazy_et.model[0].ggd[0].electrons.particles.d_radial) == 0

    dbentry.close()


def test_lazy_load_with_new_structure(requires_imas):
    dbentry = DBEntry(MEMORY_BACKEND, "ITER", 1, 1, dd_version="3.30.0")
    dbentry.create()

    eq = dbentry.factory.equilibrium()
    eq.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    eq.time = [0.0]
    eq.time_slice.resize(1)
    dbentry.put(eq)

    entry2 = DBEntry(MEMORY_BACKEND, "ITER", 1, 1, data_version="3", dd_version="4.0.0")
    entry2.open()
    lazy_eq = entry2.get("equilibrium", lazy=True)
    assert not lazy_eq.time_slice[0].boundary.dr_dz_zero_point.r.has_value


def test_lazy_load_multiple_ids(backend, worker_id, tmp_path):
    if backend == ASCII_BACKEND:
        pytest.skip("Lazy loading is not supported by the ASCII backend.")

    with open_dbentry(backend, "w", worker_id, tmp_path) as dbentry:
        cp = dbentry.factory.core_profiles()
        cp.ids_properties.homogeneous_time = 1
        cp.time = [0.0, 1.0]
        dbentry.put(cp)
        eq = dbentry.factory.equilibrium()
        eq.ids_properties.homogeneous_time = 1
        eq.time = [1.0, 2.0]
        dbentry.put(eq)

        lazy_cp = dbentry.get("core_profiles", lazy=True)
        lazy_eq = dbentry.get("equilibrium", lazy=True)
        assert all(cp.time - eq.time == -1)
        assert all(lazy_cp.time - lazy_eq.time == -1)
