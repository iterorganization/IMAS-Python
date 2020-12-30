"""A testcase checking if writing and then reading works for the latest full
data dictionary version.
"""

import logging

import pytest

from imaspy.ids_defs import IDS_TIME_MODE_HOMOGENEOUS, MEMORY_BACKEND
from imaspy.test_helpers import open_ids

root_logger = logging.getLogger("imaspy")
logger = root_logger
logger.setLevel(logging.INFO)


def test_latest_dd_manual(backend, worker_id, tmp_path):
    """Write and then read again a full IDSRoot and a single IDSToplevel."""
    ids = open_ids(backend, "w", worker_id, tmp_path)
    ids_name = "pulse_schedule"
    ids[ids_name].ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids[ids_name].ids_properties.comment = "test"

    assert ids[ids_name].ids_properties.comment.value == "test"

    ids[ids_name].put()

    if backend == MEMORY_BACKEND:
        # this one does not store anything between instantiations
        pytest.skip("Cannot open memory backend from different root")
    else:
        ids2 = open_ids(backend, "a", worker_id, tmp_path)
        ids2[ids_name].get()

        assert ids2[ids_name].ids_properties.comment.value == "test"
