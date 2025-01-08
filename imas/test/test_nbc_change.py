"""A testcase checking if writing and then reading works for the latest full
data dictionary version.

We then specifically check certain fields which have been renamed between versions,
by writing them as the old and reading as new and vice-versa
"""

import logging

import numpy as np
import pytest

from imas.db_entry import DBEntry
from imas.ids_convert import convert_ids
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS, MEMORY_BACKEND
from imas.ids_factory import IDSFactory
from imas.test.test_helpers import (
    compare_children,
    fill_with_random_data,
    open_dbentry,
)


@pytest.fixture(autouse=True)
def debug_log(caplog):
    """Make sure we capture all debug output when tests fail."""
    caplog.set_level(logging.DEBUG, "imas.ids_convert")


def test_nbc_structure_to_aos(caplog):
    # coils_non_axisymmetric/coil/conductor/cross_section was a structure in 3.39.0 and
    # is an AoS in 3.40.0 and later:
    ids = IDSFactory("3.39.0").new("coils_non_axisymmetric")
    ids.coil.resize(1)
    ids.coil[0].conductor.resize(1)
    ids.coil[0].conductor[0].cross_section.delta_r = [1.0]

    # Note: there is no corresponding attribute in DD 3.40.0, so this will just resize
    # the cross_section AoS to 1...
    ids_340 = convert_ids(ids, "3.40.0")
    assert len(ids_340.coil[0].conductor[0].cross_section) == 1

    # The reverse operation has nothing to copy, just ensure it works okay
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        convert_ids(ids_340, "3.39.0")
    assert len(caplog.record_tuples) == 0

    # Conversion reports a warning when the AOS has size >1
    ids_340.coil[0].conductor[0].cross_section.resize(2)
    with caplog.at_level(logging.WARNING):
        convert_ids(ids_340, "3.39.0")
    assert len(caplog.record_tuples) == 1
    assert caplog.record_tuples[0][:2] == ("imas.ids_convert", logging.WARNING)


def test_nbc_0d_to_1d(caplog):
    # channel/filter_spectrometer/radiance_calibration in spectrometer visible changed
    # from FLT_0D to FLT_1D in DD 3.39.0
    ids = IDSFactory("3.32.0").spectrometer_visible()
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.channel.resize(1)
    ids.channel[0].filter_spectrometer.radiance_calibration = 1.0

    # Convert to 3.39.0, when type changed to FLT_1D
    ids_339 = convert_ids(ids, "3.39.0")
    assert np.array_equal(
        ids_339.channel[0].filter_spectrometer.radiance_calibration, [1.0]
    )

    # Convert back
    ids_back = convert_ids(ids_339, "3.32.0")
    assert ids_back.channel[0].filter_spectrometer.radiance_calibration == 1.0

    # This is not supported
    ids_339.channel[0].filter_spectrometer.radiance_calibration = [1.0, 2.0]
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        ids_back = convert_ids(ids_339, "3.32.0")
    assert not ids_back.channel[0].filter_spectrometer.radiance_calibration.has_value
    assert len(caplog.record_tuples) == 1
    assert caplog.record_tuples[0][:2] == ("imas.ids_convert", logging.WARNING)

    # Test implicit conversion during get / put
    entry_339 = DBEntry(MEMORY_BACKEND, "test", 1, 1, dd_version="3.39.0")
    entry_339.create()
    entry_339.put(ids)  # implicit conversion during put()
    ids_339 = entry_339.get("spectrometer_visible")
    assert not ids_339.channel[0].filter_spectrometer.radiance_calibration.has_value

    entry_332 = DBEntry(MEMORY_BACKEND, "test", 1, 1, dd_version="3.32.0")
    entry_332.open()
    ids_back = entry_332.get("spectrometer_visible")  # implicit conversion back
    assert not ids_back.channel[0].filter_spectrometer.radiance_calibration.has_value

    # Note: closing entry_332 as well results in a double free, so we don't
    entry_339.close()


def test_nbc_change_aos_renamed():
    """Test renamed AoS in pulse_schedule: ec/antenna -> ec/launcher.

    Also tests renamed structures:
    - ec/antenna/launching_angle_pol -> ec/launcher/steering_angle_pol
    - ec/antenna/launching_angle_tor -> ec/launcher/steering_angle_tor
    """
    # AOS was renamed at v3.26.0. NBC metadata introduced in 3.28.0
    ps = IDSFactory("3.28.0").new("pulse_schedule")
    ps.ec.launcher.resize(2)
    for i in range(2):
        ps.ec.launcher[i].name = f"test{i}"

    # Test conversion from 3.28.0 -> 3.25.0
    ps2 = convert_ids(ps, "3.25.0")
    assert len(ps2.ec.antenna.value) == 2
    for i in range(2):
        assert ps2.ec.antenna[i].name == f"test{i}"

    # Test conversion from 3.25.0 -> 3.28.0
    ps3 = convert_ids(ps2, "3.28.0")
    assert len(ps3.ec.launcher.value) == 2
    for i in range(2):
        assert ps3.ec.launcher[i].name == f"test{i}"


def test_nbc_change_leaf_renamed():
    """Test renamed leaf in reflectometer_profile: position/r/data -> position/r"""
    # Leaf was renamed at 3.23.3. NBC metadata introduced in 3.28.0
    rp = IDSFactory("3.28.0").new("reflectometer_profile")
    rp.channel.resize(1)
    data = np.linspace([0, 1, 2], [1, 2, 3], 5)
    rp.channel[0].position.r = data

    # Test conversion from 3.28.0 -> 3.23.0
    rp2 = convert_ids(rp, "3.23.0")
    assert np.array_equal(rp2.channel[0].position.r.data.value, data)

    # Test conversion from 3.23.0 -> 3.28.0
    rp3 = convert_ids(rp2, "3.28.0")
    assert np.array_equal(rp3.channel[0].position.r.value, data)


def test_ids_convert_deepcopy():
    time = np.linspace(0, 1, 10)

    cp = IDSFactory("3.28.0").new("core_profiles")
    cp.time = time
    assert cp.time.value is time

    cp2 = convert_ids(cp, "3.28.0")  # Converting to the same version should also work
    assert cp2.time.value is time

    cp3 = convert_ids(cp, "3.28.0", deepcopy=True)
    assert cp3.time.value is not time
    assert np.array_equal(cp3.time.value, time)


def test_pulse_schedule_aos_renamed_up(backend, worker_id, tmp_path):
    """pulse_schedule/ec/launcher was renamed from pulse_schedule/ec/antenna
    in version 3.26.0."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.28.0")
    ids = IDSFactory("3.25.0").new("pulse_schedule")
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.ec.antenna.resize(1)
    ids.ec.antenna[0].name = "test"

    # Test automatic conversion up
    dbentry.put(ids)

    # Now load back and ensure no conversion is done
    ids2 = dbentry.get("pulse_schedule")
    assert ids2.ec.launcher[0].name.value == "test"
    dbentry.close()


def test_pulse_schedule_aos_renamed_autodetect_up(backend, worker_id, tmp_path):
    """pulse_schedule/ec/launcher was renamed from pulse_schedule/ec/antenna
    in version 3.26.0."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.25.0")
    ids = dbentry.factory.new("pulse_schedule")
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.ec.antenna.resize(1)
    ids.ec.antenna[0].name = "test"

    # No conversion required
    dbentry.put(ids)

    # Now load back with a newer dbentry version, which does a conversion
    dbentry2 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.28.0")
    ids2 = dbentry2.get("pulse_schedule")
    assert ids2.ec.launcher[0].name.value == "test"

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_pulse_schedule_aos_renamed_down(backend, worker_id, tmp_path):
    """pulse_schedule/ec/launcher was renamed from pulse_schedule/ec/antenna
    in version 3.26.0."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.25.0")
    ids = IDSFactory("3.28.0").new("pulse_schedule")
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.ec.launcher.resize(1)
    ids.ec.launcher[0].name = "test"

    # Test automatic conversion down
    dbentry.put(ids)

    # Now load back and ensure no conversion is done
    ids2 = dbentry.get("pulse_schedule")
    assert ids2.ec.antenna[0].name.value == "test"

    dbentry.close()


def test_pulse_schedule_aos_renamed_autodetect_down(backend, worker_id, tmp_path):
    """pulse_schedule/ec/launcher was renamed from pulse_schedule/ec/antenna
    in version 3.26.0."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.28.0")
    ids = dbentry.factory.new("pulse_schedule")
    ids.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
    ids.ec.launcher.resize(1)
    ids.ec.launcher[0].name = "test"

    # No conversion required
    dbentry.put(ids)

    # Now load back with a newer dbentry version, which does a conversion
    dbentry2 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.25.0")
    ids2 = dbentry2.get("pulse_schedule")
    assert ids2.ec.antenna[0].name.value == "test"

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_pulse_schedule_aos_renamed_autofill_up(backend, worker_id, tmp_path):
    """pulse_schedule/ec/launcher was renamed from pulse_schedule/ec/antenna
    in version 3.26.0."""
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.25.0")
    ids = IDSFactory("3.28.0").new("pulse_schedule")
    fill_with_random_data(ids)
    dbentry.put(ids)

    ids2 = dbentry.get("pulse_schedule")

    # test the antenna/launcher only
    assert len(ids.ec.launcher.value) == len(ids2.ec.antenna.value)
    for ch1, ch2 in zip(ids.ec.launcher, ids2.ec.antenna):
        # compare_children does not work since also the fields were changed.
        # manually check the common fields
        assert ch1.name == ch2.name
        assert ch1.identifier == ch2.identifier
        assert ch1.power_type.name == ch2.power_type.name
        assert ch1.power_type.index == ch2.power_type.index
        for new, old in [
            (ch1.power, ch2.power),
            (ch1.frequency, ch2.frequency),
            (ch1.deposition_rho_tor_norm, ch2.deposition_rho_tor_norm),
            (ch1.steering_angle_pol, ch2.launching_angle_pol),
            (ch1.steering_angle_tor, ch2.launching_angle_tor),
        ]:
            assert new.reference_name == old.reference_name
            for name in ["data", "data_error_upper", "data_error_lower", "time"]:
                assert np.array_equal(new.reference[name], old.reference[name])
            assert new.reference.data_error_index == old.reference.data_error_index
            assert np.array_equal(new.reference.time, old.reference.time)
            assert new.reference_type == old.reference_type
            assert new.envelope_type == old.envelope_type
    dbentry.close()


def test_pulse_schedule_multi_rename():
    # Multiple renames of the same element:
    # DD >= 3.40+:  ec/beam
    # DD 3.26-3.40: ec/launcher (but NBC metadata added in 3.28 only)
    # DD < 3.26:    ec/antenna
    ps = {
        version: IDSFactory(version).new("pulse_schedule")
        for version in ["3.25.0", "3.30.0", "3.39.0", "3.40.0"]
    }
    for ids in ps.values():
        ids.ids_properties.homogeneous_time = 0
    name = "This is the name of the first item in the AOS"
    ps["3.25.0"].ec.antenna.resize(1)
    ps["3.25.0"].ec.antenna[0].name = name
    ps["3.30.0"].ec.launcher.resize(1)
    ps["3.30.0"].ec.launcher[0].name = name
    ps["3.39.0"].ec.launcher.resize(1)
    ps["3.39.0"].ec.launcher[0].name = name
    ps["3.40.0"].ec.beam.resize(1)
    ps["3.40.0"].ec.beam[0].name = name

    for version1 in ps:
        for version2 in ps:
            converted = convert_ids(ps[version1], version2)
            compare_children(ps[version2], converted)


def test_autofill_save_newer(ids_name, backend, worker_id, tmp_path):
    """Create an ids, autofill it, save it as a newer version, read it back
    and check that it's the same.

    TODO: we should also check newer IDSes, since this only checks variables that
    existed in 3.25.0. Doing all versions for all IDSes is too slow however.
    """
    dbentry = open_dbentry(backend, "w", worker_id, tmp_path, dd_version="3.30.0")
    factory = IDSFactory(version="3.25.0")
    if not factory.exists(ids_name):
        pytest.skip("IDS %s not defined for version 3.25.0" % (ids_name,))
    ids = factory.new(ids_name)
    fill_with_random_data(ids)

    dbentry.put(ids)

    dbentry2 = open_dbentry(backend, "r", worker_id, tmp_path, dd_version="3.25.0")
    ids2 = dbentry2.get(ids_name)

    # Some elements were removed between 3.25.0 and 3.30.0, so the conversion discards
    # the affected data. Pass as deleted_paths to compare_children
    deleted_paths = {
        "coils_non_axisymmetric": {"is_periodic", "coils_n"},
        "ece": {"channel/harmonic/data"},
        "langmuir_probes": {
            "embedded/j_ion_parallel/data",
            "embedded/j_ion_parallel/validity_timed",
            "embedded/j_ion_parallel/validity",
            "reciprocating/plunge/potential_floating",
            "reciprocating/plunge/t_e",
            "reciprocating/plunge/t_i",
            "reciprocating/plunge/saturation_current_ion",
            "reciprocating/plunge/heat_flux_parallel",
        },
        "magnetics": {"method/diamagnetic_flux/data"},
        "pulse_schedule": {
            "ec/antenna/phase/reference_name",
            "ec/antenna/phase/reference/data",
            "ec/antenna/phase/reference/time",
            "ec/antenna/phase/reference_type",
            "ec/antenna/phase/envelope_type",
        },
        "spectrometer_x_ray_crystal": {
            "camera/center/r",
            "camera/center/z",
            "camera/center/phi",
        },
    }.get(ids_name, [])
    compare_children(ids, ids2, deleted_paths=deleted_paths)

    # Compare outcome of implicit conversion at put with explicit convert_ids
    implicit_3_30 = dbentry.get(ids_name)
    explicit_3_30 = convert_ids(ids, version="3.30.0")
    compare_children(implicit_3_30, explicit_3_30)

    # Compare outcome of explicit conversion back to 3.25.0
    compare_children(ids2, convert_ids(explicit_3_30, "3.25.0"))

    dbentry.close()
    if backend != MEMORY_BACKEND:  # MEM backend already cleaned up, prevent SEGFAULT
        dbentry2.close()


def test_convert_min_to_max_v3(ids_name, latest_factory3):
    """Convert from DD 3.22.0 to the last DDv3 release."""
    factory = IDSFactory("3.22.0")
    if not factory.exists(ids_name):
        pytest.skip("IDS %s not defined for version 3.22.0" % (ids_name,))
    if not latest_factory3.exists(ids_name):
        pytest.skip(f"IDS {ids_name} not defined for version {latest_factory3.version}")

    ids = factory.new(ids_name)
    fill_with_random_data(ids)
    convert_ids(ids, latest_factory3.version)


def test_convert_max_to_min_v3(ids_name, latest_factory3):
    """Convert from the last DDv3 release to DD 3.22.0."""
    factory = IDSFactory("3.22.0")
    if not factory.exists(ids_name):
        pytest.skip(f"IDS {ids_name} not defined for version 3.22.0")
    if not latest_factory3.exists(ids_name):
        pytest.skip(f"IDS {ids_name} not defined for version {latest_factory3.version}")

    ids = latest_factory3.new(ids_name)
    fill_with_random_data(ids)
    convert_ids(ids, None, factory=factory)


def test_convert_3_to_newest(ids_name, latest_factory3, latest_factory):
    """Convert from the last DDv3 release to the last released DD."""
    if not latest_factory3.exists(ids_name) or not latest_factory.exists(ids_name):
        pytest.skip(f"IDS {ids_name} not defined for both versions.")

    ids = latest_factory3.new(ids_name)
    fill_with_random_data(ids)
    convert_ids(ids, None, factory=latest_factory)


def test_convert_newest_to_3(ids_name, latest_factory3, latest_factory):
    """Convert from the last released DD to the last DDv3 release."""
    if not latest_factory3.exists(ids_name) or not latest_factory.exists(ids_name):
        pytest.skip(f"IDS {ids_name} not defined for both versions.")

    ids = latest_factory.new(ids_name)
    fill_with_random_data(ids)
    convert_ids(ids, None, factory=latest_factory3)
