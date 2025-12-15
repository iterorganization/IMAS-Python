# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.

import numpy as np
import pytest

from imas.ids_factory import IDSFactory
from imas.ids_slice import IDSSlice


@pytest.fixture
def wall_with_units():
    return create_wall_with_units()


@pytest.fixture
def wall_varying_sizes():
    return create_wall_with_units(total_units=2, element_counts=[4, 2])


def create_wall_with_units(
    total_units: int = 12,
    element_counts=None,
    *,
    dd_version: str = "3.39.0",
):

    if total_units < 2:
        raise ValueError("Need at least two units to exercise slice edge cases.")

    wall = IDSFactory(dd_version).wall()
    wall.description_2d.resize(1)

    units = wall.description_2d[0].vessel.unit
    units.resize(total_units)

    if element_counts is None:
        element_counts = [4, 2] + [3] * (total_units - 2)

    element_counts = list(element_counts)
    if len(element_counts) != total_units:
        raise ValueError("element_counts length must match total_units.")

    for unit_idx, unit in enumerate(units):
        unit.name = f"unit-{unit_idx}"
        unit.element.resize(element_counts[unit_idx])
        for elem_idx, element in enumerate(unit.element):
            element.name = f"element-{unit_idx}-{elem_idx}"

    return wall


def safe_element_lookup(units_slice, element_index: int):
    collected = []
    skipped_units = []
    for idx, unit in enumerate(units_slice):
        elements = unit.element
        if element_index >= len(elements):
            skipped_units.append(idx)
            continue
        collected.append(elements[element_index].name.value)
    return {"collected": collected, "skipped_units": skipped_units}


class TestBasicSlicing:

    def test_slice_with_start_and_stop(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        result = cp.profiles_1d[3:7]
        assert isinstance(result, IDSSlice)
        assert len(result) == 4

        result = cp.profiles_1d[::2]
        assert isinstance(result, IDSSlice)
        assert len(result) == 5

        result = cp.profiles_1d[-5:]
        assert isinstance(result, IDSSlice)
        assert len(result) == 5

    def test_slice_corner_cases(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        result = cp.profiles_1d[0:100]
        assert len(result) == 10

        result = cp.profiles_1d[10:20]
        assert len(result) == 0

        result = cp.profiles_1d[::-1]
        assert len(result) == 10

    def test_integer_index_still_works(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        result = cp.profiles_1d[5]
        assert not isinstance(result, IDSSlice)
        assert hasattr(result, "_path")


class TestIDSSlicePath:

    def test_slice_path_representation(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        result = cp.profiles_1d[5:8]
        expected_path = "[5:8]"
        assert expected_path in result._path

        result = cp.profiles_1d[5:8][1:3]
        assert "[" in result._path

    def test_attribute_access_path(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit[8:]

        element_slice = units.element
        assert "element" in element_slice._path


class TestIDSSliceIteration:

    def test_iteration_and_len(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)

        slice_obj = cp.profiles_1d[1:4]

        items = list(slice_obj)
        assert len(items) == 3

        assert len(slice_obj) == 3


class TestIDSSliceIndexing:

    def test_integer_indexing_slice(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        slice_obj = cp.profiles_1d[3:7]
        element = slice_obj[1]
        assert not isinstance(element, IDSSlice)

    def test_slice_indexing_slice(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        slice_obj = cp.profiles_1d[2:8]
        nested_slice = slice_obj[1:4]
        assert isinstance(nested_slice, IDSSlice)
        assert len(nested_slice) == 3


class TestIDSSliceAttributeAccess:

    def test_attribute_access_nested_attributes(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit[8:]

        names = units.name
        assert isinstance(names, IDSSlice)
        assert len(names) == 4

        units_full = wall.description_2d[0].vessel.unit
        elements = units_full[:].element
        assert isinstance(elements, IDSSlice)


class TestIDSSliceRepr:

    def test_repr_count_display(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        slice_obj = cp.profiles_1d[5:6]
        repr_str = repr(slice_obj)
        assert "IDSSlice" in repr_str
        assert "1 item" in repr_str

        slice_obj = cp.profiles_1d[5:8]
        repr_str = repr(slice_obj)
        assert "IDSSlice" in repr_str
        assert "3 items" in repr_str


class TestWallExampleSlicing:

    def test_wall_units_nested_element_access(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit

        units_slice = units[8:]
        assert isinstance(units_slice, IDSSlice)
        assert len(units_slice) == 4

        elements_slice = units_slice.element
        assert isinstance(elements_slice, IDSSlice)


class TestEdgeCases:

    def test_slice_empty_array(self):
        cp = IDSFactory("3.39.0").core_profiles()

        result = cp.profiles_1d[:]
        assert isinstance(result, IDSSlice)
        assert len(result) == 0

    def test_slice_single_element(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(1)

        result = cp.profiles_1d[:]
        assert isinstance(result, IDSSlice)
        assert len(result) == 1

    def test_invalid_step_zero(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        with pytest.raises(ValueError):
            cp.profiles_1d[::0]


class TestFlatten:

    def test_flatten_basic_and_partial(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)

        for profile in cp.profiles_1d:
            profile.ion.resize(5)

        slice_obj = cp.profiles_1d[:].ion
        flattened = slice_obj[:]
        assert isinstance(flattened, IDSSlice)
        assert len(flattened) == 15

        cp2 = IDSFactory("3.39.0").core_profiles()
        cp2.profiles_1d.resize(4)
        for profile in cp2.profiles_1d:
            profile.ion.resize(3)
        flattened2 = cp2.profiles_1d[:2].ion[:]
        assert len(flattened2) == 6

    def test_flatten_empty_and_single(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(2)
        empty_flattened = cp.profiles_1d[:].ion[:]
        assert len(empty_flattened) == 0

        cp2 = IDSFactory("3.39.0").core_profiles()
        cp2.profiles_1d.resize(1)
        cp2.profiles_1d[0].ion.resize(4)
        single_flattened = cp2.profiles_1d[:].ion[:]
        assert len(single_flattened) == 4

    def test_flatten_indexing_and_slicing(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(2)

        for i, profile in enumerate(cp.profiles_1d):
            profile.ion.resize(3)
            for j, ion in enumerate(profile.ion):
                ion.label = f"ion_{i}_{j}"

        flattened = cp.profiles_1d[:].ion[:]

        assert flattened[0].label == "ion_0_0"
        assert flattened[3].label == "ion_1_0"

        subset = flattened[1:4]
        assert isinstance(subset, IDSSlice)
        assert len(subset) == 3
        labels = [ion.label for ion in subset]
        assert labels == ["ion_0_1", "ion_0_2", "ion_1_0"]

    def test_flatten_repr_and_path(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(2)
        for profile in cp.profiles_1d:
            profile.ion.resize(2)

        flattened = cp.profiles_1d[:].ion[:]
        repr_str = repr(flattened)

        assert "IDSSlice" in repr_str
        assert "4 items" in repr_str
        assert "[:]" in flattened._path

    def test_flatten_complex_case(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit[:5]

        all_elements = units.element[:]
        assert len(all_elements) == 4 + 2 + 3 + 3 + 3


class TestVaryingArraySizeIndexing:

    def test_unit_slice_element_integer_indexing(self, wall_varying_sizes):
        units = wall_varying_sizes.description_2d[0].vessel.unit
        units_slice = units[:2]
        element_slice = units_slice.element

        with pytest.raises(IndexError):
            element_slice[2]

    def test_unit_slice_element_safe_indexing_scenarios(self, wall_varying_sizes):
        units = wall_varying_sizes.description_2d[0].vessel.unit
        units_slice = units[:2]

        result = safe_element_lookup(units_slice, 1)
        assert len(result["collected"]) == 2
        assert result["collected"] == ["element-0-1", "element-1-1"]

        result = safe_element_lookup(units_slice, 2)
        assert len(result["collected"]) == 1
        assert result["skipped_units"] == [1]

        result = safe_element_lookup(units_slice, 4)
        assert len(result["collected"]) == 0
        assert result["skipped_units"] == [0, 1]

    def test_unit_slice_element_individual_access(self, wall_varying_sizes):
        units = wall_varying_sizes.description_2d[0].vessel.unit
        element_slice = units[:2].element

        first_from_each = element_slice[0]
        assert isinstance(first_from_each, IDSSlice)
        assert len(first_from_each) == 2

        arrays = list(element_slice)
        assert len(arrays[0]) == 4
        assert arrays[0][2].name.value == "element-0-2"

        assert len(arrays[1]) == 2

        with pytest.raises(IndexError):
            arrays[1][2]

    def test_wall_with_diverse_element_counts(self):
        wall = create_wall_with_units(total_units=5, element_counts=[3, 1, 4, 2, 5])

        units = wall.description_2d[0].vessel.unit
        units_slice = units[:3]
        element_slice = units_slice.element

        first_from_each = element_slice[0]
        assert isinstance(first_from_each, IDSSlice)
        assert len(first_from_each) == 3

        arrays = list(element_slice)
        assert len(arrays[0]) == 3
        assert len(arrays[2]) == 4

        result = safe_element_lookup(units_slice, 2)
        assert len(result["collected"]) == 2
        assert result["skipped_units"] == [1]


class TestIDSSliceValues:

    def test_values_basic_extraction(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit

        names_slice = units[:].name
        names = names_slice.values()

        assert isinstance(names, list)
        assert len(names) == 12
        assert all(isinstance(name, str) and name.startswith("unit-") for name in names)
        assert names == [f"unit-{i}" for i in range(12)]

    def test_values_integer_and_float_extraction(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)

        for profile in cp.profiles_1d:
            profile.ion.resize(2)
            for i, ion in enumerate(profile.ion):
                ion.neutral_index = i
                ion.z_ion = float(i + 1)

        ions = cp.profiles_1d[:].ion[:]
        indices = ions[:].neutral_index.values()
        assert all(isinstance(idx, (int, np.integer)) for idx in indices)

        z_values = ions[:].z_ion.values()
        assert all(isinstance(z, (float, np.floating)) for z in z_values)

    def test_values_partial_and_empty_slices(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit

        names = units[:5].name.values()
        assert len(names) == 5
        assert names == [f"unit-{i}" for i in range(5)]

        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        # Empty slices should raise IndexError when accessing attributes
        with pytest.raises(IndexError):
            cp.profiles_1d[5:10].label.values()

    def test_values_with_step_and_negative_indices(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit

        names_step = units[::2].name.values()
        assert len(names_step) == 6
        assert names_step == [f"unit-{i}" for i in range(0, 12, 2)]

        names_neg = units[-3:].name.values()
        assert len(names_neg) == 3
        assert names_neg == [f"unit-{i}" for i in range(9, 12)]

    def test_values_structure_preservation(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)

        for profile in cp.profiles_1d:
            profile.ion.resize(2)

        ions = cp.profiles_1d[:].ion[:].values()

        assert len(ions) == 6
        for ion in ions:
            assert hasattr(ion, "_path")
            from imas.ids_primitive import IDSPrimitive

            assert not isinstance(ion, IDSPrimitive)

    def test_values_array_primitives(self):
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(2)

        cp.profiles_1d[0].grid.psi = np.linspace(0, 1, 10)
        cp.profiles_1d[1].grid.psi = np.linspace(1, 2, 10)

        psi_values = cp.profiles_1d[:].grid.psi.values()

        assert len(psi_values) == 2
        assert all(isinstance(psi, np.ndarray) for psi in psi_values)

    def test_values_consistency_with_iteration(self, wall_with_units):
        wall = wall_with_units
        units = wall.description_2d[0].vessel.unit

        names_via_values = units[:5].name.values()

        names_via_iteration = [unit.name.value for unit in units[:5]]

        assert names_via_values == names_via_iteration
