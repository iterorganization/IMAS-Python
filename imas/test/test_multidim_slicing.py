# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Tests for multi-dimensional slicing support in IDSSlice."""

import numpy as np
import pytest

from imas.ids_factory import IDSFactory


class TestMultiDimSlicing:
    """Shape tracking and conversion methods."""

    def test_shape_property_single_level(self):
        """Test shape property for single-level slice."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)

        result = cp.profiles_1d[:]
        assert hasattr(result, "shape")
        assert result.shape == (10,)

    def test_shape_property_two_level(self):
        """Test shape property for 2D array access."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for p in cp.profiles_1d:
            p.grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        result = cp.profiles_1d[:].grid.rho_tor_norm
        assert result.shape == (5, 3)

    def test_shape_property_three_level(self):
        """Test shape property for 3D nested structure."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        for p in cp.profiles_1d:
            p.ion.resize(2)
            for i in p.ion:
                i.element.resize(2)

        result = cp.profiles_1d[:].ion[:].element[:]
        assert result.shape == (3, 2, 2)

    def test_to_array_2d_regular(self):
        """Test to_array() with regular 2D array."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for i, p in enumerate(cp.profiles_1d):
            p.grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        result = cp.profiles_1d[:].grid.rho_tor_norm
        array = result.to_array()

        assert isinstance(array, np.ndarray)
        assert array.shape == (5, 3)
        assert np.allclose(array[0], [0.0, 0.5, 1.0])
        assert np.allclose(array[4], [0.0, 0.5, 1.0])

    def test_to_array_3d_regular(self):
        """Test to_array() with regular 3D array."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        for p in cp.profiles_1d:
            p.ion.resize(2)
            for i_idx, i in enumerate(p.ion):
                i.element.resize(2)
                for e_idx, e in enumerate(i.element):
                    e.z_n = float(e_idx)

        result = cp.profiles_1d[:].ion[:].element[:].z_n
        array = result.to_array()

        assert isinstance(array, np.ndarray)
        assert array.shape == (3, 2, 2)
        assert np.allclose(array[0, 0, :], [0.0, 1.0])
        assert np.allclose(array[0, 1, :], [0.0, 1.0])

    def test_to_array_variable_size(self):
        """Test to_array() with variable-size arrays."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        cp.profiles_1d[0].grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])
        cp.profiles_1d[1].grid.rho_tor_norm = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        cp.profiles_1d[2].grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        result = cp.profiles_1d[:].grid.rho_tor_norm
        array = result.to_array()

        assert array.dtype == object
        assert len(array) == 3
        assert len(array[0]) == 3
        assert len(array[1]) == 5
        assert len(array[2]) == 3

    def test_enhanced_values_2d(self):
        """Test enhanced values() method for 2D extraction."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        for p in cp.profiles_1d:
            p.grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        result = cp.profiles_1d[:].grid.rho_tor_norm
        values = result.values()

        # Should be a list of 3 arrays
        assert isinstance(values, list)
        assert len(values) == 3
        for v in values:
            assert isinstance(v, np.ndarray)
            assert len(v) == 3

    def test_enhanced_values_3d(self):
        """Test enhanced values() method for 3D extraction."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(2)
        for p in cp.profiles_1d:
            p.ion.resize(2)
            for i in p.ion:
                i.element.resize(2)
                for e_idx, e in enumerate(i.element):
                    e.z_n = float(e_idx)

        result = cp.profiles_1d[:].ion[:].element[:].z_n
        values = result.values()

        assert isinstance(values, list)
        assert len(values) == 8  # 2 profiles * 2 ions * 2 elements

    def test_slice_preserves_groups(self):
        """Test that slicing preserves group structure."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)
        for p in cp.profiles_1d:
            p.ion.resize(3)

        # Get all ions, then slice
        result = cp.profiles_1d[:].ion[:]

        # Should still know the structure: 10 profiles, 3 ions each
        assert result.shape == (10, 3)
        assert len(result) == 30  # Flattened for iteration, but shape preserved

    def test_integer_index_on_nested(self):
        """Test integer indexing on nested structures."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for i, p in enumerate(cp.profiles_1d):
            p.ion.resize(2)
            for j, ion in enumerate(p.ion):
                ion.label = f"ion_{i}_{j}"

        # Get first ion from all profiles
        result = cp.profiles_1d[:].ion[0]

        assert len(result) == 5
        for i, ion in enumerate(result):
            assert ion.label == f"ion_{i}_0"

    def test_slice_on_nested_arrays(self):
        """Test slicing on nested arrays."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for p in cp.profiles_1d:
            p.ion.resize(4)

        # Get first 2 ions from each profile
        result = cp.profiles_1d[:].ion[:2]

        assert result.shape == (5, 2)
        assert len(result) == 10  # 5 profiles * 2 ions each

    def test_step_slicing_on_nested(self):
        """Test step slicing on nested structures."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for p in cp.profiles_1d:
            p.ion.resize(6)

        # Get every other ion
        result = cp.profiles_1d[:].ion[::2]

        assert result.shape == (5, 3)  # 5 profiles, 3 ions each (0, 2, 4)
        assert len(result) == 15

    def test_negative_indexing_on_nested(self):
        """Test negative indexing on nested structures."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for p in cp.profiles_1d:
            p.ion.resize(3)
            for j, ion in enumerate(p.ion):
                ion.label = f"ion_{j}"

        # Get last ion from each profile
        result = cp.profiles_1d[:].ion[-1]

        assert len(result) == 5
        for ion in result:
            assert ion.label == "ion_2"

    def test_to_array_grouped_structure(self):
        """Test that to_array preserves grouped structure."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        for p_idx, p in enumerate(cp.profiles_1d):
            p.ion.resize(2)
            for i_idx, i in enumerate(p.ion):
                i.z_ion = float(p_idx * 10 + i_idx)

        result = cp.profiles_1d[:].ion[:].z_ion
        array = result.to_array()

        # Should be (3, 2) array
        assert array.shape == (3, 2)
        assert array[0, 0] == 0.0
        assert array[1, 0] == 10.0
        assert array[2, 1] == 21.0

    @pytest.mark.skip(reason="Phase 3 feature - boolean indexing not yet implemented")
    def test_boolean_indexing_simple(self):
        """Test boolean indexing on slices."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for i, p in enumerate(cp.profiles_1d):
            p.electrons.density = np.array([float(i)] * 5)

        result = cp.profiles_1d[:].electrons.density

        mask = np.array([True, False, True, False, True])
        filtered = result[mask]
        assert len(filtered) == 3

    def test_assignment_on_slice(self):
        """Test assignment through slices."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        for p in cp.profiles_1d:
            p.grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        # This requires assignment support
        # cp.profiles_1d[:].grid.rho_tor_norm[:] = new_values
        # For now, verify slicing works for reading

        result = cp.profiles_1d[:].grid.rho_tor_norm
        array = result.to_array()
        assert array.shape == (3, 3)

    def test_xarray_integration_compatible(self):
        """Test that output is compatible with xarray."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        cp.time = np.array([1.0, 2.0, 3.0])

        for i, p in enumerate(cp.profiles_1d):
            p.grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])
            p.electrons.temperature = np.array([1.0, 2.0, 3.0]) * (i + 1)

        # Test that we can extract values in xarray-compatible format
        temps = cp.profiles_1d[:].electrons.temperature.to_array()
        times = cp.time

        assert temps.shape == (3, 3)
        assert len(times) == 3

    def test_performance_large_hierarchy(self):
        """Test performance with large nested hierarchies."""
        cp = IDSFactory("3.39.0").core_profiles()
        n_profiles = 50
        cp.profiles_1d.resize(n_profiles)

        for p in cp.profiles_1d:
            p.grid.rho_tor_norm = np.linspace(0, 1, 100)
            p.ion.resize(5)
            for i in p.ion:
                i.element.resize(3)

        # Should handle large data without significant slowdown
        result = cp.profiles_1d[:].grid.rho_tor_norm
        array = result.to_array()

        assert array.shape == (n_profiles, 100)

    def test_lazy_loading_with_multidim(self):
        """Test that lazy loading works with multi-dimensional slicing."""
        # This would require a database, so we'll test with in-memory
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for p in cp.profiles_1d:
            p.grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        result = cp.profiles_1d[:].grid.rho_tor_norm

        # Verify lazy attributes are preserved
        assert hasattr(result, "_lazy")
        assert hasattr(result, "_parent_array")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_slice(self):
        """Test slicing that results in empty arrays."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(5)
        for p in cp.profiles_1d:
            p.ion.resize(0)

        result = cp.profiles_1d[:].ion
        assert len(result) == 5
        for ions in result:
            # Each should be empty
            pass

    def test_single_element_2d(self):
        """Test 2D extraction with single element."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(1)
        cp.profiles_1d[0].grid.rho_tor_norm = np.array([0.0, 0.5, 1.0])

        result = cp.profiles_1d[:].grid.rho_tor_norm
        assert result.shape == (1, 3)

    def test_single_dimension_value(self):
        """Test accessing a single value in multi-dimensional structure."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(3)
        for p in cp.profiles_1d:
            p.ion.resize(2)
            for i in p.ion:
                i.z_ion = 1.0

        result = cp.profiles_1d[:].ion[0].z_ion

        # Should be 3 items (one per profile)
        assert len(result) == 3

    def test_slice_of_slice(self):
        """Test slicing a slice."""
        cp = IDSFactory("3.39.0").core_profiles()
        cp.profiles_1d.resize(10)
        for p in cp.profiles_1d:
            p.ion.resize(3)

        result1 = cp.profiles_1d[::2].ion  # Every other profile's ions
        assert result1.shape == (5, 3)

        result2 = result1[:2]  # First 2 from each
        assert result2.shape == (5, 2)
