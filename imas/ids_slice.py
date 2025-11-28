# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""IDSSlice represents a collection of IDS nodes matching a slice expression.

This module provides the IDSSlice class, which enables slicing of arrays of
structures while maintaining the hierarchy and allowing further operations on
the resulting collection.
"""

import logging
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple, Union

import numpy as np

from imas.ids_metadata import IDSMetadata

if TYPE_CHECKING:
    from imas.ids_struct_array import IDSStructArray

logger = logging.getLogger(__name__)


class IDSSlice:
    """Represents a slice of IDS struct array elements.

    When slicing an IDSStructArray, instead of returning a regular Python list,
    an IDSSlice is returned. This allows for:
    - Tracking the slice operation in the path
    - Further slicing of child elements
    - Child node access on all matched elements
    - Iteration over matched elements

    Attributes:
        metadata: Metadata from the parent array, or None if not available
    """

    __slots__ = [
        "metadata",
        "_matched_elements",
        "_slice_path",
        "_parent_array",
        "_virtual_shape",
        "_element_hierarchy",
    ]

    def __init__(
        self,
        metadata: Optional[IDSMetadata],
        matched_elements: List[Any],
        slice_path: str,
        parent_array: Optional["IDSStructArray"] = None,
        virtual_shape: Optional[Tuple[int, ...]] = None,
        element_hierarchy: Optional[List[Any]] = None,
    ):
        """Initialize IDSSlice.

        Args:
            metadata: Metadata from the parent array
            matched_elements: List of elements that matched the slice
            slice_path: String representation of the slice operation (e.g., "[8:]")
            parent_array: Optional reference to the parent IDSStructArray for context
            virtual_shape: Optional tuple representing multi-dimensional shape
            element_hierarchy: Optional tracking of element grouping
        """
        self.metadata = metadata
        self._matched_elements = matched_elements
        self._slice_path = slice_path
        self._parent_array = parent_array
        self._virtual_shape = virtual_shape or (len(matched_elements),)
        self._element_hierarchy = element_hierarchy or [len(matched_elements)]

    @property
    def _path(self) -> str:
        """Return the path representation of this slice."""
        return self._slice_path

    @property
    def shape(self) -> Tuple[int, ...]:
        """Get the virtual multi-dimensional shape.
        
        Returns the shape of the data as if it were organized in a multi-dimensional
        array, based on the hierarchy of slicing operations performed.
        
        Returns:
            Tuple of dimensions. Use with caution for jagged arrays where sizes vary.
        """
        return self._virtual_shape

    def __len__(self) -> int:
        """Return the number of elements matched by this slice."""
        return len(self._matched_elements)

    def __iter__(self) -> Iterator[Any]:
        """Iterate over all matched elements."""
        return iter(self._matched_elements)

    def __getitem__(self, item: Union[int, slice]) -> Union[Any, "IDSSlice"]:
        """Get element(s) from the slice.

        When the matched elements are IDSStructArray objects, the indexing
        operation is applied to each array element (array-wise indexing).
        Otherwise, the operation is applied to the matched elements list itself.

        Args:
            item: Index or slice to apply

        Returns:
            - IDSSlice: If item is a slice, or if applying integer index to
              IDSStructArray elements
            - Single element: If item is an int and elements are not IDSStructArray
        """
        from imas.ids_struct_array import IDSStructArray

        # Array-wise indexing: apply operation to each IDSStructArray element
        if self._matched_elements and isinstance(
            self._matched_elements[0], IDSStructArray
        ):
            if isinstance(item, slice):
                # NEW: Preserve structure instead of flattening
                sliced_elements = []
                sliced_sizes = []
                
                for array in self._matched_elements:
                    sliced = array[item]
                    if isinstance(sliced, IDSSlice):
                        sliced_elements.extend(sliced._matched_elements)
                        sliced_sizes.append(len(sliced))
                    else:
                        sliced_elements.append(sliced)
                        sliced_sizes.append(1)

                slice_str = self._format_slice(item)
                new_path = self._slice_path + slice_str

                # NEW: Update shape to reflect the sliced structure
                # Keep first dimensions, update last dimension
                new_virtual_shape = self._virtual_shape[:-1] + (sliced_sizes[0] if sliced_sizes else 0,)
                new_hierarchy = self._element_hierarchy[:-1] + [sliced_sizes]

                return IDSSlice(
                    self.metadata,
                    sliced_elements,
                    new_path,
                    parent_array=self._parent_array,
                    virtual_shape=new_virtual_shape,
                    element_hierarchy=new_hierarchy,
                )
            else:
                # Integer indexing on arrays
                indexed_elements = []
                for array in self._matched_elements:
                    indexed_elements.append(array[int(item)])

                new_path = self._slice_path + f"[{item}]"

                # Shape changes: last dimension becomes 1
                new_virtual_shape = self._virtual_shape[:-1] + (1,)

                return IDSSlice(
                    self.metadata,
                    indexed_elements,
                    new_path,
                    parent_array=self._parent_array,
                    virtual_shape=new_virtual_shape,
                    element_hierarchy=self._element_hierarchy,
                )
        else:
            if isinstance(item, slice):
                sliced_elements = self._matched_elements[item]
                slice_str = self._format_slice(item)
                new_path = self._slice_path + slice_str

                # NEW: Update shape to reflect the slice on first dimension
                new_virtual_shape = (len(sliced_elements),) + self._virtual_shape[1:]
                new_element_hierarchy = [len(sliced_elements)] + self._element_hierarchy[1:]

                return IDSSlice(
                    self.metadata,
                    sliced_elements,
                    new_path,
                    parent_array=self._parent_array,
                    virtual_shape=new_virtual_shape,
                    element_hierarchy=new_element_hierarchy,
                )
            else:
                return self._matched_elements[int(item)]

    def __getattr__(self, name: str) -> "IDSSlice":
        """Access a child node on all matched elements.

        This returns a new IDSSlice containing the child node from
        each matched element. Preserves multi-dimensional structure
        when child elements are arrays.

        Args:
            name: Name of the node to access

        Returns:
            A new IDSSlice containing the child node from each matched element
        """
        if not self._matched_elements:
            raise IndexError(
                f"Cannot access node '{name}' on empty slice with 0 elements"
            )

        from imas.ids_struct_array import IDSStructArray

        child_metadata = None
        if self.metadata is not None:
            try:
                child_metadata = self.metadata[name]
            except (KeyError, TypeError):
                pass

        child_elements = [getattr(element, name) for element in self]
        new_path = self._slice_path + "." + name

        # Check if children are IDSStructArray (nested arrays) or IDSNumericArray
        if not child_elements:
            # Empty slice
            return IDSSlice(
                child_metadata,
                child_elements,
                new_path,
                parent_array=self._parent_array,
                virtual_shape=self._virtual_shape,
                element_hierarchy=self._element_hierarchy,
            )

        from imas.ids_primitive import IDSNumericArray

        if isinstance(child_elements[0], IDSStructArray):
            # Children are IDSStructArray - track the new dimension
            child_sizes = [len(arr) for arr in child_elements]
            
            # New virtual shape: current shape + new dimension
            new_virtual_shape = self._virtual_shape + (child_sizes[0] if child_sizes else 0,)
            new_hierarchy = self._element_hierarchy + [child_sizes]
            
            return IDSSlice(
                child_metadata,
                child_elements,
                new_path,
                parent_array=self._parent_array,
                virtual_shape=new_virtual_shape,
                element_hierarchy=new_hierarchy,
            )
        elif isinstance(child_elements[0], IDSNumericArray):
            # Children are IDSNumericArray - track the array dimension
            # Each IDSNumericArray has a size (length of its data)
            child_sizes = [len(arr) for arr in child_elements]
            
            # New virtual shape: current shape + new dimension (size of first numeric array)
            # Note: For now we assume all have same size (regular array)
            # Jagged arrays handled by to_array() with object dtype
            new_virtual_shape = self._virtual_shape + (child_sizes[0] if child_sizes else 0,)
            new_hierarchy = self._element_hierarchy + [child_sizes]
            
            return IDSSlice(
                child_metadata,
                child_elements,
                new_path,
                parent_array=self._parent_array,
                virtual_shape=new_virtual_shape,
                element_hierarchy=new_hierarchy,
            )
        else:
            # Children are not arrays (structures or other primitives)
            return IDSSlice(
                child_metadata,
                child_elements,
                new_path,
                parent_array=self._parent_array,
                virtual_shape=self._virtual_shape,
                element_hierarchy=self._element_hierarchy,
            )

    def __repr__(self) -> str:
        """Build a string representation of this IDSSlice.

        Returns a string showing:
        - The IDS type name (e.g., 'equilibrium')
        - The full path including the slice operation (e.g., 'time_slice[:]')
        - The number of matched elements

        Returns:
            String representation like below
            like '<IDSSlice (IDS:equilibrium, time_slice[:] with 106 matches)>'
        """
        from imas.util import get_toplevel, get_full_path

        my_repr = f"<{type(self).__name__}"
        ids_name = "unknown"
        full_path = self._path

        if self._parent_array is not None:
            ids_name = get_toplevel(self._parent_array).metadata.name
            parent_array_path = get_full_path(self._parent_array)
            full_path = parent_array_path + self._path
        item_word = "item" if len(self) == 1 else "items"
        my_repr += f" (IDS:{ids_name}, {full_path} with {len(self)} {item_word})>"
        return my_repr

    def values(self, reshape: bool = False) -> Any:
        """Extract raw values from elements in this slice.

        For IDSPrimitive elements, this extracts the wrapped value.
        For other element types, returns them as-is.

        For multi-dimensional slices (when shape has multiple dimensions),
        this extracts values respecting the multi-dimensional structure.

        This is useful for getting the actual data without the IDS wrapper
        when accessing scalar fields through a slice, without requiring
        explicit looping through the original collection.

        Args:
            reshape: If True, reshape result to match self.shape for
                    multi-dimensional slices. If False (default), return flat list
                    or list of extracted values.

        Returns:
            For 1D: List of raw Python/numpy values or unwrapped elements
            For multi-D with reshape=False: List of elements (each being an array)
            For multi-D with reshape=True: numpy.ndarray with shape self.shape,
                        or nested lists/object array representing structure

        Examples:
            >>> # Get names from identifiers without looping
            >>> n = edge_profiles.grid_ggd[0].grid_subset[:].identifier.name.values()
            >>> # Result: ["nodes", "edges", "cells"]
            >>>
            >>> # Get 2D array but as list of arrays (default)
            >>> rho = core_profiles.profiles_1d[:].grid.rho_tor.values()
            >>> # Result: [ndarray(100,), ndarray(100,), ...] - list of 106 arrays
            >>>
            >>> # Get 2D array reshaped to (106, 100)
            >>> rho = core_profiles.profiles_1d[:].grid.rho_tor.values(reshape=True)
            >>> # Result: ndarray shape (106, 100)
            >>>
            >>> # 3D ions case - returns object array with structure
            >>> ion_rho = core_profiles.profiles_1d[:].ion[:].element[:].density.values(reshape=True)
            >>> # Result: object array shape (106, 3, 2) with IDSNumericArray elements
        """
        from imas.ids_primitive import IDSPrimitive, IDSNumericArray

        # Default behavior: return flat list without reshape
        if not reshape:
            result = []
            for element in self._matched_elements:
                if isinstance(element, IDSPrimitive):
                    result.append(element.value)
                else:
                    result.append(element)
            return result

        # Multi-dimensional case with reshape requested
        flat_values = []
        for element in self._matched_elements:
            if isinstance(element, IDSPrimitive):
                flat_values.append(element.value)
            elif isinstance(element, IDSNumericArray):
                flat_values.append(element.data if hasattr(element, 'data') else element.value)
            else:
                flat_values.append(element)

        # For 1D, just return as is
        if len(self._virtual_shape) == 1:
            return flat_values

        # Try to reshape to multi-dimensional shape
        try:
            # Calculate total size
            total_size = 1
            for dim in self._virtual_shape:
                total_size *= dim

            # Check if sizes match
            if len(flat_values) == total_size:
                # Successfully reshape to multi-dimensional
                return np.array(flat_values, dtype=object).reshape(self._virtual_shape)
        except (ValueError, TypeError):
            pass

        # If reshape fails or not all elements are extractable, return as object array
        try:
            return np.array(flat_values, dtype=object).reshape(self._virtual_shape[0:1])
        except (ValueError, TypeError):
            return flat_values

    def to_array(self) -> np.ndarray:
        """Convert this slice to a numpy array respecting multi-dimensional structure.

        For 1D slices, returns a simple 1D array.
        For multi-dimensional slices, returns an array with shape self.shape.
        For jagged arrays (varying sizes in lower dimensions), returns an object array.

        This is useful for integration with numpy operations, scipy functions,
        and xarray data structures. The returned array preserves the hierarchical
        structure of the IMAS data.

        Returns:
            numpy.ndarray with shape self.shape. For jagged arrays, dtype will be object.

        Raises:
            ValueError: If array cannot be converted to numpy

        Examples:
            >>> # Convert 2D slice to numpy array
            >>> rho_array = core_profiles.profiles_1d[:].grid.rho_tor.to_array()
            >>> # Result: ndarray shape (106, 100), dtype float64
            >>> print(rho_array.shape)
            (106, 100)
            >>>
            >>> # Jagged array returns object array
            >>> ion_density = core_profiles.profiles_1d[:].ion[:].density.to_array()
            >>> # Result: object array shape (106, 3) with varying sizes
            >>>
            >>> # Can be used directly with numpy functions
            >>> mean_rho = np.mean(rho_array, axis=1)
            >>> # Result: (106,) array of mean values
        """
        from imas.ids_primitive import IDSPrimitive, IDSNumericArray

        # 1D case - simple conversion
        if len(self._virtual_shape) == 1:
            flat_values = []
            for element in self._matched_elements:
                if isinstance(element, IDSPrimitive):
                    flat_values.append(element.value)
                else:
                    flat_values.append(element)
            try:
                return np.array(flat_values)
            except (ValueError, TypeError):
                return np.array(flat_values, dtype=object)

        # Multi-dimensional case
        # Check if matched elements are themselves arrays (IDSNumericArray)
        if self._matched_elements and isinstance(self._matched_elements[0], IDSNumericArray):
            # Elements are numeric arrays - extract their values and stack them
            array_values = []
            for element in self._matched_elements:
                if isinstance(element, IDSNumericArray):
                    array_values.append(element.value)
                else:
                    array_values.append(element)
            
            # Try to stack into proper shape
            try:
                # Check if all arrays have the same size (regular)
                sizes = []
                for val in array_values:
                    if hasattr(val, '__len__'):
                        sizes.append(len(val))
                    else:
                        sizes.append(1)
                
                # If all sizes are the same, we can create a regular array
                if len(set(sizes)) == 1:
                    # Regular array - all sub-arrays same size
                    stacked = np.array(array_values)
                    # Should now have shape (first_dim, second_dim)
                    if stacked.shape == self._virtual_shape:
                        return stacked
                    else:
                        # Try explicit reshape
                        try:
                            return stacked.reshape(self._virtual_shape)
                        except ValueError:
                            # If reshape fails, return as object array
                            result_arr = np.empty(self._virtual_shape, dtype=object)
                            for i, val in enumerate(array_values):
                                result_arr.flat[i] = val
                            return result_arr
                else:
                    # Jagged array - different sizes
                    result_arr = np.empty(self._virtual_shape[0], dtype=object)
                    for i, val in enumerate(array_values):
                        result_arr[i] = val
                    return result_arr
            except (ValueError, TypeError) as e:
                # Fallback: return object array
                result_arr = np.empty(self._virtual_shape[0], dtype=object)
                for i, val in enumerate(array_values):
                    result_arr[i] = val
                return result_arr

        # For non-numeric elements in multi-dimensional structure
        # Extract and try to build structure
        flat_values = []
        for element in self._matched_elements:
            if isinstance(element, IDSPrimitive):
                flat_values.append(element.value)
            else:
                flat_values.append(element)

        total_size = 1
        for dim in self._virtual_shape:
            total_size *= dim

        # Check if we have the right number of elements
        if len(flat_values) != total_size:
            raise ValueError(
                f"Cannot convert to array: expected {total_size} elements "
                f"but got {len(flat_values)}"
            )

        # Try to create the array
        try:
            arr = np.array(flat_values)
            try:
                # Try to reshape to target shape
                return arr.reshape(self._virtual_shape)
            except (ValueError, TypeError):
                # If reshape fails, use object array
                arr_obj = np.empty(self._virtual_shape, dtype=object)
                for i, val in enumerate(flat_values):
                    arr_obj.flat[i] = val
                return arr_obj
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to convert slice to numpy array: {e}")

    @staticmethod
    def _format_slice(slice_obj: slice) -> str:
        """Format a slice object as a string.

        Args:
            slice_obj: The slice object to format

        Returns:
            String representation like "[1:5]", "[::2]", etc.
        """
        start = slice_obj.start if slice_obj.start is not None else ""
        stop = slice_obj.stop if slice_obj.stop is not None else ""
        step = slice_obj.step if slice_obj.step is not None else ""

        if step:
            return f"[{start}:{stop}:{step}]"
        else:
            return f"[{start}:{stop}]"
