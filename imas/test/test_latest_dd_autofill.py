"""A testcase checking if writing and then reading works for the latest full
data dictionary version.
"""

import copy

import pytest

from imas.ids_defs import (
    ASCII_SERIALIZER_PROTOCOL,
    FLEXBUFFERS_SERIALIZER_PROTOCOL,
    MEMORY_BACKEND,
)
from imas.ids_factory import IDSFactory
from imas.test.test_helpers import (
    compare_children,
    fill_with_random_data,
    open_dbentry,
)
from imas.util import visit_children


def test_latest_dd_autofill_consistency(ids_name):
    ids = IDSFactory().new(ids_name)
    fill_with_random_data(ids)

    # check that each element in ids has _parent set.
    visit_children(has_parent, ids, leaf_only=False)


def has_parent(child):
    """Check that the child has _parent set"""
    assert child._parent is not None


def test_latest_dd_autofill(ids_name, backend, worker_id, tmp_path):
    """Write and then read again all IDSToplevels."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path)
    ids = IDSFactory().new(ids_name)
    fill_with_random_data(ids)

    dbentry.put(ids)
    ids_ref = copy.deepcopy(ids)
    # the deepcopy comes after the put() since that updates dd version and AL lang

    dbentry2 = open_dbentry(backend, "a", worker_id, tmp_path)
    ids = dbentry2.get(ids_name)
    compare_children(ids, ids_ref)

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


@pytest.mark.parametrize(
    "serializer", [ASCII_SERIALIZER_PROTOCOL, FLEXBUFFERS_SERIALIZER_PROTOCOL]
)
def test_latest_dd_autofill_serialize(serializer, ids_name, has_imas):
    """Serialize and then deserialize again all IDSToplevels"""
    if serializer is None:
        pytest.skip("Unsupported serializer")

    factory = IDSFactory()
    ids = factory.new(ids_name)
    fill_with_random_data(ids)

    if not has_imas:
        return  # rest of the test requires an IMAS install
    data = ids.serialize(serializer)

    ids2 = factory.new(ids_name)
    ids2.deserialize(data)

    compare_children(ids, ids2)
