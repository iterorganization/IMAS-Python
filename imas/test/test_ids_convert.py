# Unit tests for ids_convert.py.
# See also integration tests for conversions in test_nbc_change.py

import logging
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import numpy
import pytest

from imas import identifiers
from imas.ids_convert import (
    _get_ctxpath,
    _get_tbp,
    convert_ids,
    dd_version_map_from_factories,
    iter_parents,
)
from imas.ids_defs import (
    ASCII_BACKEND,
    IDS_TIME_MODE_HETEROGENEOUS,
    IDS_TIME_MODE_HOMOGENEOUS,
    IDS_TIME_MODE_INDEPENDENT,
    MEMORY_BACKEND,
)
from imas.ids_factory import IDSFactory
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure
from imas.test.test_helpers import compare_children, open_dbentry

UTC = timezone.utc


def test_iter_parents():
    assert list(iter_parents("a/b/c/d/e")) == ["a", "a/b", "a/b/c", "a/b/c/d"]
    assert list(iter_parents("abc/def/g")) == ["abc", "abc/def"]


def test_dd_version_map_from_factories_invalid_version():
    factory1 = IDSFactory(version="3.39.0")
    factory2 = MagicMock()
    factory2._version = "3.30.0-123-12345678"
    factory2._etree = factory1._etree

    version_map, factory1_is_oldest = dd_version_map_from_factories(
        "core_profiles", factory1, factory2
    )
    assert not factory1_is_oldest
    # maps should be empty, since we set the same etree on factory2
    assert not version_map.new_to_old.path
    assert not version_map.old_to_new.path


@pytest.fixture()
def factory():
    return IDSFactory(version="3.38.0")


@pytest.fixture()
def core_profiles_paths(factory):
    etree = factory._etree
    cp = etree.find("IDS[@name='core_profiles']")
    return {field.get("path", ""): field for field in cp.iterfind(".//field")}


def test_aos_and_ctxpath(core_profiles_paths):
    paths = core_profiles_paths
    f = _get_ctxpath
    assert f("time", paths) == "time"
    assert f("profiles_1d", paths) == "profiles_1d"
    assert f("profiles_1d/time", paths) == "time"
    assert f("profiles_1d/grid/rho_tor_norm", paths) == "grid/rho_tor_norm"
    assert f("profiles_1d/ion", paths) == "ion"
    assert f("profiles_1d/ion/element", paths) == "element"
    assert f("profiles_1d/ion/element/z_n", paths) == "z_n"


def test_timebasepath(core_profiles_paths):
    paths = core_profiles_paths
    f = _get_tbp
    assert f(paths["time"], paths) == "time"
    assert f(paths["profiles_1d"], paths) == "profiles_1d/time"
    assert f(paths["profiles_1d/grid"], paths) == ""


def test_compare_timebasepath_functions(ids_name):
    # Ensure that the two timebasepath implementations are consistent
    ids = IDSFactory().new(ids_name)
    ids_element = ids.metadata._structure_xml
    paths = {field.get("path", ""): field for field in ids_element.iterfind(".//field")}

    def recurse(structure: IDSStructure, ctx_path: str):
        for item in structure:
            name = item.metadata.name
            new_path = f"{ctx_path}/{name}" if ctx_path else name

            tbp1 = _get_tbp(item.metadata._structure_xml, paths)
            tbp2 = item.metadata.timebasepath
            assert tbp1 == tbp2

            if isinstance(item, IDSStructure):
                recurse(item, new_path)
            else:
                if isinstance(item, IDSStructArray):
                    item.resize(1)
                    recurse(item[0], "")

    recurse(ids, "")


def test_dbentry_autoconvert1(backend, worker_id, tmp_path):
    entry_331 = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.31.0")
    old_factory = entry_331.factory
    old_ids = old_factory.new("core_profiles")
    old_ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS

    # Put without conversion:
    entry_331.put(old_ids)
    assert old_ids.ids_properties.version_put.data_dictionary == "3.31.0"
    if backend != MEMORY_BACKEND:
        entry_331.close()

    entry_342 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.42.0")

    # Get without conversion
    old_ids_get = entry_342.get("core_profiles", autoconvert=False)
    assert old_ids_get.ids_properties.version_put.data_dictionary == "3.31.0"
    assert old_ids_get._dd_version == "3.31.0"

    # Work around ASCII backend bug...
    if backend == ASCII_BACKEND:
        entry_342.close()
        entry_342 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.42.0")

    # Get with conversion
    new_ids_get = entry_342.get("core_profiles")
    assert new_ids_get.ids_properties.version_put.data_dictionary == "3.31.0"
    assert new_ids_get._dd_version == "3.42.0"

    entry_342.close()


def test_dbentry_autoconvert2(backend, worker_id, tmp_path):
    entry_342 = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.42.0")
    new_ids = entry_342.factory.new("core_profiles")
    new_ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS

    # Put without conversion:
    entry_342.put(new_ids)
    assert new_ids.ids_properties.version_put.data_dictionary == "3.42.0"
    if backend != MEMORY_BACKEND:
        entry_342.close()

    entry_331 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.31.0")

    # Get without conversion
    new_ids_get = entry_331.get("core_profiles", autoconvert=False)
    assert new_ids_get.ids_properties.version_put.data_dictionary == "3.42.0"
    assert new_ids_get._dd_version == "3.42.0"

    # Work around ASCII backend bug...
    if backend == ASCII_BACKEND:
        entry_331.close()
        entry_331 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.31.0")

    # Get with conversion
    old_ids_get = entry_331.get("core_profiles")
    assert old_ids_get.ids_properties.version_put.data_dictionary == "3.42.0"
    assert old_ids_get._dd_version == "3.31.0"

    entry_331.close()


def test_provenance_entry(factory):
    cp = factory.core_profiles()
    # Note: DD 3.31.0 doesn't have the provenance data structure, test that it doesn't
    # report an error:
    cp2 = convert_ids(cp, "3.31.0", provenance_origin_uri="<testdata>")
    # Convert back to 3.38.0
    cp3 = convert_ids(cp2, "3.38.0", provenance_origin_uri="<testdata>")
    assert len(cp3.ids_properties.provenance.node) == 1
    assert cp3.ids_properties.provenance.node[0].path == ""
    assert len(cp3.ids_properties.provenance.node[0].sources) == 1
    provenance_txt = cp3.ids_properties.provenance.node[0].sources[0]
    # Check that the provided origin URI is in the text
    assert "<testdata>" in provenance_txt
    # Check that origin and destination DD versions are included
    assert "3.31.0" in provenance_txt
    assert "3.38.0" in provenance_txt
    # Check that imas-python is mentioned
    assert "imas-python" in provenance_txt

    # Test logic branch for node.reference implemented with IMAS-5304
    cp4 = convert_ids(cp2, "3.42.0", provenance_origin_uri="<testdata>")
    assert len(cp4.ids_properties.provenance.node) == 1
    assert cp4.ids_properties.provenance.node[0].path == ""
    assert len(cp4.ids_properties.provenance.node[0].reference) == 1
    assert "<testdata>" in cp4.ids_properties.provenance.node[0].reference[0].name
    timestamp = str(cp4.ids_properties.provenance.node[0].reference[0].timestamp)
    # Check that timestamp adheres to the format YYYY-MM-DDTHH:MM:SSZ
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp)
    dtime = datetime.now(UTC) - datetime.fromisoformat(timestamp)
    assert timedelta(seconds=0) <= dtime < timedelta(seconds=2)


@pytest.fixture
def dd4factory():
    return IDSFactory("4.0.0")


def test_3to4_ggd_space_identifier(dd4factory):
    ep = IDSFactory("3.39.0").edge_profiles()
    ep.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    ep.grid_ggd.resize(1)
    ep.grid_ggd[0].time = 0.0
    ep.grid_ggd[0].space.resize(1)
    ep.grid_ggd[0].space[0].coordinates_type = numpy.array([1, 2], dtype=numpy.int32)

    ep4 = convert_ids(ep, None, factory=dd4factory)
    cid = identifiers.coordinate_identifier
    assert ep4.grid_ggd[0].time == 0.0
    coordinates_type = ep4.grid_ggd[0].space[0].coordinates_type
    assert len(coordinates_type) == 2
    for i in range(2):
        # Test that the full identifier structure is filled:
        identifier = cid(i + 1)
        assert coordinates_type[i].index == identifier.index
        assert coordinates_type[i].name == identifier.name
        assert coordinates_type[i].description == identifier.description

    ep3 = convert_ids(ep4, "3.39.0")
    compare_children(ep, ep3)


def test_3to4_repeat_children_first_point_conditional(dd4factory):
    # The wall IDS contains all (four!) cases with conditional repeats
    wall = IDSFactory("3.39.0").wall()
    wall.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    wall.description_2d.resize(2)

    # Case 1: repeat_children_first_point_conditional
    wall.description_2d[0].vessel.unit.resize(2)
    for i in range(2):
        outline_inner = wall.description_2d[0].vessel.unit[i].annular.outline_inner
        outline_inner.closed = i  # first is open, second is closed
        outline_inner.r = [1.0, 2.0, 3.0]
        outline_inner.z = [-1.0, -2.0, -3.0]

    # Case 2: repeat_children_first_point_conditional_sibling
    wall.description_2d[0].limiter.unit.resize(2)
    for i in range(2):
        unit = wall.description_2d[0].limiter.unit[i]
        unit.closed = i  # first is open, second is closed
        unit.outline.r = [1.0, 2.0, 3.0]
        unit.outline.z = [-1.0, -2.0, -3.0]

    # Case 3: repeat_children_first_point_conditional_sibling_dynamic
    wall.description_2d[0].mobile.unit.resize(2)
    for i in range(2):
        unit = wall.description_2d[0].mobile.unit[i]
        unit.closed = i  # first is open, second is closed
        unit.outline.resize(3)
        for j in range(3):
            unit.outline[j].r = [1.0, 2.0, 3.0]
            unit.outline[j].z = [-1.0, -2.0, -3.0]
            unit.outline[j].time = j / 5

    # Case 4: repeat_children_first_point_conditional_centreline
    # (see https://jira.iter.org/browse/IMAS-5541)
    wall.description_2d[1].vessel.unit.resize(2)
    for i in range(2):
        centreline = wall.description_2d[1].vessel.unit[i].annular.centreline
        centreline.closed = i  # first is open, second is closed
        centreline.r = [1.0, 2.0, 3.0]
        centreline.z = [-1.0, -2.0, -3.0]
        # if it was open there were too many thickness values!
        # The last one will be dropped and repeated
        wall.description_2d[1].vessel.unit[i].annular.thickness = [1, 0.9, 0.9]

    wall4 = convert_ids(wall, None, factory=dd4factory)
    assert len(wall4.description_2d) == 2

    # Test conversion for case 1:
    assert len(wall4.description_2d[0].vessel.unit) == 2
    for i in range(2):
        outline_inner = wall4.description_2d[0].vessel.unit[i].annular.outline_inner
        if i == 0:  # open outline, first point not repeated:
            assert numpy.array_equal(outline_inner.r, [1.0, 2.0, 3.0])
            assert numpy.array_equal(outline_inner.z, [-1.0, -2.0, -3.0])
        else:  # closed outline, first point repeated:
            assert numpy.array_equal(outline_inner.r, [1.0, 2.0, 3.0, 1.0])
            assert numpy.array_equal(outline_inner.z, [-1.0, -2.0, -3.0, -1.0])

    # Test conversion for case 2:
    assert len(wall4.description_2d[0].limiter.unit) == 2
    for i in range(2):
        unit = wall4.description_2d[0].limiter.unit[i]
        if i == 0:  # open outline, first point not repeated:
            assert numpy.array_equal(unit.outline.r, [1.0, 2.0, 3.0])
            assert numpy.array_equal(unit.outline.z, [-1.0, -2.0, -3.0])
        else:  # closed outline, first point repeated:
            assert numpy.array_equal(unit.outline.r, [1.0, 2.0, 3.0, 1.0])
            assert numpy.array_equal(unit.outline.z, [-1.0, -2.0, -3.0, -1.0])

    # Test conversion for case 3:
    assert len(wall4.description_2d[0].mobile.unit) == 2
    for i in range(2):
        unit = wall4.description_2d[0].mobile.unit[i]
        for j in range(3):
            if i == 0:  # open outline, first point not repeated:
                assert numpy.array_equal(unit.outline[j].r, [1.0, 2.0, 3.0])
                assert numpy.array_equal(unit.outline[j].z, [-1.0, -2.0, -3.0])
            else:  # closed outline, first point repeated:
                assert numpy.array_equal(unit.outline[j].r, [1.0, 2.0, 3.0, 1.0])
                assert numpy.array_equal(unit.outline[j].z, [-1.0, -2.0, -3.0, -1.0])
            assert unit.outline[j].time == pytest.approx(j / 5)

    # Test conversion for case 4:
    assert len(wall4.description_2d[1].vessel.unit) == 2
    for i in range(2):
        thickness = wall4.description_2d[1].vessel.unit[i].annular.thickness
        if i == 0:  # open outline, there was one value too many, drop the last one
            assert numpy.array_equal(thickness, [1, 0.9])
        else:  # closed outline, thickness values kept
            assert numpy.array_equal(thickness, [1, 0.9, 0.9])

    # Test conversion back
    wall3 = convert_ids(wall4, "3.39.0")
    compare_children(wall, wall3)


def test_3to4_repeat_children_first_point(dd4factory):
    iron_core = IDSFactory("3.39.0").iron_core()
    iron_core.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    iron_core.segment.resize(1)
    iron_core.segment[0].geometry.outline.r = [1.0, 2.0, 3.0]
    iron_core.segment[0].geometry.outline.z = [-1.0, -2.0, -3.0]

    iron_core4 = convert_ids(iron_core, None, factory=dd4factory)
    geometry = iron_core4.segment[0].geometry
    assert numpy.array_equal(geometry.outline.r, [1.0, 2.0, 3.0, 1.0])
    assert numpy.array_equal(geometry.outline.z, [-1.0, -2.0, -3.0, -1.0])

    iron_core3 = convert_ids(iron_core4, "3.39.0")
    compare_children(iron_core, iron_core3)


def test_3to4_cocos_change(dd4factory):
    cp = IDSFactory("3.39.0").core_profiles()
    cp.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    cp.time = [1.0]
    cp.profiles_1d.resize(1)
    cp.profiles_1d[0].grid.rho_tor_norm = numpy.linspace(0, 1, 11)
    cp.profiles_1d[0].grid.psi = numpy.linspace(10, 20, 11)

    cp4 = convert_ids(cp, None, factory=dd4factory)
    assert numpy.array_equal(
        cp4.profiles_1d[0].grid.rho_tor_norm,
        cp.profiles_1d[0].grid.rho_tor_norm,
    )
    assert numpy.array_equal(
        cp4.profiles_1d[0].grid.psi,
        -cp.profiles_1d[0].grid.psi,
    )

    cp3 = convert_ids(cp4, "3.39.0")
    compare_children(cp, cp3)


def test_3to4_circuit_connections(dd4factory, caplog):
    pfa = IDSFactory("3.39.0").pf_active()
    pfa.ids_properties.homogeneous_time = IDS_TIME_MODE_HETEROGENEOUS
    pfa.circuit.resize(1)
    pfa.circuit[0].connections = [
        [0, 1, 0, 0, 1, 0],
        [0, 0, 1, 0, 0, 1],
        [1, 0, 0, 1, 0, 0],
    ]

    pfa4 = convert_ids(pfa, None, factory=dd4factory)
    assert numpy.array_equal(
        pfa4.circuit[0].connections, [[-1, 0, 1], [0, 1, -1], [1, -1, 0]]
    )

    pfa3 = convert_ids(pfa4, "3.39.0")
    compare_children(pfa, pfa3)

    # Test invalid connections shape
    pfa.circuit[0].connections = [
        [0, 1, 0, 0, 1, 0, 1],
        [0, 0, 1, 0, 0, 1, 1],
        [1, 0, 0, 1, 0, 0, 1],
    ]
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        pfa4 = convert_ids(pfa, None, factory=dd4factory)
    # Incorrect shape, data is not converted:
    assert numpy.array_equal(pfa.circuit[0].connections, pfa4.circuit[0].connections)
    # Check that a message with ERROR severity was logged
    assert len(caplog.record_tuples) == 1
    assert caplog.record_tuples[0][1] == logging.ERROR


def test_3to4_cocos_magnetics_workaround(dd4factory):
    mag = IDSFactory("3.39.0").magnetics()
    mag.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    mag.flux_loop.resize(1)
    mag.flux_loop[0].flux.data = [1.0, 2.0]

    mag4 = convert_ids(mag, None, factory=dd4factory)
    assert numpy.array_equal(mag4.flux_loop[0].flux.data, [-1.0, -2.0])

    mag3 = convert_ids(mag4, "3.39.0")
    compare_children(mag, mag3)
