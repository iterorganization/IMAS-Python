"""A testcase checking if writing and then reading works for the latest full
data dictionary version.
"""

import logging
import os

import numpy as np
import pytest

from imas.backends.imas_core.mdsplus_model import ensure_data_dir, mdsplus_model_dir
from imas.ids_defs import (
    ASCII_BACKEND,
    CLOSEST_INTERP,
    IDS_TIME_MODE_HETEROGENEOUS,
    IDS_TIME_MODE_HOMOGENEOUS,
    MDSPLUS_BACKEND,
)
from imas.ids_factory import IDSFactory
from imas.test.test_helpers import open_dbentry

# import IMAS HLI, skip module when this is an install without IMAS
imas = pytest.importorskip("imas")

logger = logging.getLogger(__name__)


@pytest.fixture(params=(IDS_TIME_MODE_HOMOGENEOUS, IDS_TIME_MODE_HETEROGENEOUS))
def time_mode(request):
    return request.param


def test_write_read_time(backend, worker_id, tmp_path, time_mode):
    """Write some data to an IDS and then check that all slices match."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    eq = IDSFactory().new("equilibrium")
    eq.ids_properties.homogeneous_time = time_mode

    eq.time = np.array([0.0, 0.1, 0.2])
    dbentry.put(eq)

    eq = dbentry.get("equilibrium")
    assert np.array_equal(eq.time, [0.0, 0.1, 0.2])
    dbentry.close()


def test_time_slicing_get(backend, worker_id, tmp_path, time_mode):
    """Write some data to an IDS and then check that all slices match."""
    if backend == ASCII_BACKEND:
        pytest.skip("ASCII backend does not support slice mode")
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    eq = IDSFactory().new("equilibrium")
    eq.ids_properties.homogeneous_time = time_mode

    # eq.time is the time coordinate for b0 in heterogeneous mode as well
    eq.time = np.array([0.0, 0.1, 0.2])
    eq.vacuum_toroidal_field.b0 = np.array([3.0, 4.0, 5.0])
    dbentry.put(eq)

    for time in range(3):
        eq = dbentry.get_slice("equilibrium", time * 0.1, CLOSEST_INTERP)
        assert eq.vacuum_toroidal_field.b0.value == time + 3.0
    dbentry.close()


def test_time_slicing_put(backend, worker_id, tmp_path, request, time_mode):
    """Write some slices to an IDS and then check that they are all there"""
    if backend == ASCII_BACKEND:
        pytest.skip("ASCII backend does not support slice mode")
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    eq = IDSFactory().new("equilibrium")
    eq.ids_properties.homogeneous_time = time_mode

    for time in range(3):
        # eq.time is the time coordinate for b0 in heterogeneous mode as well
        eq.time = [time * 0.1]
        eq.vacuum_toroidal_field.b0 = [time + 3.0]
        dbentry.put_slice(eq)

    eq = dbentry.get("equilibrium")

    assert np.allclose(eq.vacuum_toroidal_field.b0.value, [3.0, 4.0, 5.0])
    assert np.allclose(eq.time.value, [0.0, 0.1, 0.2])
    dbentry.close()


@pytest.mark.skip(reason="skipping hli test")
def test_hli_time_slicing_put(backend, worker_id, tmp_path, time_mode):
    """Write some slices to an IDS and then check that they are all there"""
    if backend == ASCII_BACKEND:
        pytest.skip("ASCII backend does not support slice mode")

    ids = imas.equilibrium()

    if worker_id == "master":
        pulse = 1
    else:
        pulse = int(worker_id[2:]) + 1

    # ensure presence of mdsplus model dir
    if backend == MDSPLUS_BACKEND:
        os.environ["ids_path"] = mdsplus_model_dir(IDSFactory())
        ensure_data_dir(str(tmp_path), "test", "3", 9999)
    db_entry = imas.DBEntry(backend, "test", pulse, 9999, user_name=str(tmp_path))
    status, ctx = db_entry.create()
    if status != 0:
        logger.error("Error opening db entry %s", status)

    ids.ids_properties.homogeneous_time = time_mode

    for time in range(3):
        ids.vacuum_toroidal_field.b0 = np.asarray([time + 3.0])
        # eq.time is the time coordinate for b0 in heterogeneous mode as well
        ids.time = np.asarray([time * 0.1])
        ids.putSlice(0, db_entry)

    ids.get(0, db_entry)

    db_entry.close()

    assert np.allclose(ids.vacuum_toroidal_field.b0, [3.0, 4.0, 5.0])
    assert np.allclose(ids.time, [0.0, 0.1, 0.2])


def test_time_slicing_put_two(backend, worker_id, tmp_path, time_mode):
    """Write some slices to an IDS and then check that they are all there"""
    if backend == ASCII_BACKEND:
        pytest.skip("ASCII backend does not support slice mode")
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    eq = IDSFactory().new("equilibrium")
    eq.ids_properties.homogeneous_time = time_mode

    for time in range(3):
        eq.vacuum_toroidal_field.b0 = [time + 3.0, time + 3.5]
        # eq.time is the time coordinate for b0 in heterogeneous mode as well
        eq.time = [time * 0.1, (time + 0.5) * 0.1]
        dbentry.put_slice(eq)

    eq = dbentry.get("equilibrium")

    assert np.array_equal(
        eq.vacuum_toroidal_field.b0.value, [3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
    )
    # Use allclose instead of array_equal since 0.15000000000000002 != 0.15
    assert np.allclose(eq.time.value, [0.0, 0.05, 0.1, 0.15, 0.2, 0.25])
    dbentry.close()


def test_time_slicing_time_mode(backend, worker_id, tmp_path, time_mode):
    """Write data to controllers IDS to test heterogeneous time mode."""
    if backend == ASCII_BACKEND:
        pytest.skip("ASCII backend does not support slice mode")
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    ctrls = IDSFactory().new("controllers")
    ctrls.ids_properties.homogeneous_time = time_mode

    ctrls.time = [0.1, 0.2, 0.3]
    ctrls.linear_controller.resize(2)
    # This time base is ignored for IDS_TIME_MODE_HOMOGENEOUS
    ctrls.linear_controller[0].inputs.time = [0.0, 0.1, 0.2]
    ctrls.linear_controller[0].inputs.data = [[0.0, 1.0, 2.0]]
    # This time base is ignored for IDS_TIME_MODE_HOMOGENEOUS
    ctrls.linear_controller[1].inputs.time = [0.2, 0.3, 0.4]
    ctrls.linear_controller[1].inputs.data = [[0.0, 1.0, 2.0]]
    # code.output_flag always uses /time as timebase
    ctrls.code.output_flag = [0, 1, 2]

    dbentry.put(ctrls)
    ctrls = dbentry.get_slice("controllers", 0.2, CLOSEST_INTERP)
    assert np.array_equal(ctrls.time.value, [0.2])
    if time_mode == IDS_TIME_MODE_HETEROGENEOUS:
        assert np.array_equal(ctrls.linear_controller[0].inputs.time.value, [0.2])
        assert np.array_equal(ctrls.linear_controller[0].inputs.data.value, [[2.0]])
        assert np.array_equal(ctrls.linear_controller[1].inputs.time.value, [0.2])
        assert np.array_equal(ctrls.linear_controller[1].inputs.data.value, [[0.0]])
    else:  # HOMOGENEOUS_TIME
        # Note: don't test time arrays of linear_controller inputs, as they shouldn't be
        # used in homogeneous time mode
        assert np.array_equal(ctrls.linear_controller[0].inputs.data.value, [[1.0]])
        assert np.array_equal(ctrls.linear_controller[1].inputs.data.value, [[1.0]])
    assert np.array_equal(ctrls.code.output_flag.value, [1])
    dbentry.close()
