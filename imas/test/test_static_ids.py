# Testing static IDS behavior as defined in IMAS-3330

import logging

import pytest

import imas
from imas.ids_defs import IDS_TIME_MODE_HETEROGENEOUS, IDS_TIME_MODE_INDEPENDENT
from imas.ids_metadata import IDSType


def test_ids_valid_type():
    factory = imas.IDSFactory()
    ids_types = set()
    for ids_name in factory:
        ids = factory.new(ids_name)
        ids_types.add(ids.metadata.type)

    # For DD versions <4, `type` is never set at IDS top levels.
    # For DD versions >=4, `type` may be CONSTANT (i.e. no root time node) or DYNAMIC
    assert ids_types in ({IDSType.NONE}, {IDSType.CONSTANT, IDSType.DYNAMIC})


def test_constant_ids(caplog):
    ids = imas.IDSFactory().new("amns_data")
    if ids.metadata.type is IDSType.NONE:
        pytest.skip("IDS definition has no constant IDSs")

    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    dbe = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "test", 0, 0)
    dbe.create()

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="imas"):
        dbe.put(ids)
    assert ids.ids_properties.homogeneous_time == IDS_TIME_MODE_INDEPENDENT
    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert "ids_properties/homogeneous_time has been set to 2" in msg
