# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""IDSSlice represents a collection of IDS nodes matching a slice expression.

This module provides the IDSSlice class, which enables slicing of arrays of
structures while maintaining the hierarchy and allowing further operations on
the resulting collection.
"""

import logging
from typing import Any, Iterator, List, Union

from imas.ids_metadata import IDSMetadata

logger = logging.getLogger(__name__)


class IDSSlice:
    """Represents a slice of IDS struct array elements.

    When slicing an IDSStructArray, instead of returning a regular Python list,
    an IDSSlice is returned. This allows for:
    - Tracking the slice operation in the path
    - Further slicing of child elements
    - Attribute access on all matched elements
    - Iteration over matched elements
    """

    __slots__ = ["metadata", "_matched_elements", "_slice_path"]

    def __init__(
        self,
        metadata: IDSMetadata,
        matched_elements: List[Any],
        slice_path: str,
    ):
        """Initialize IDSSlice.

        Args:
            metadata: Metadata from the parent array
            matched_elements: List of elements that matched the slice
            slice_path: String representation of the slice operation (e.g., "[8:]")
        """
        self.metadata = metadata
        self._matched_elements = matched_elements
        self._slice_path = slice_path

    @property
    def _path(self) -> str:
        """Return the path representation of this slice."""
        return self._slice_path

    def __len__(self) -> int:
        """Return the number of elements matched by this slice."""
        return len(self._matched_elements)

    def __iter__(self) -> Iterator[Any]:
        """Iterate over all matched elements."""
        return iter(self._matched_elements)

    def __getitem__(self, item: Union[int, slice]) -> Union[Any, "IDSSlice"]:
        """Get element(s) from the slice.

        Args:
            item: Index or slice to apply to the matched elements

        Returns:
            A single element if item is an int, or an IDSSlice if item is a slice
        """
        if isinstance(item, slice):
            # Further slice the matched elements
            sliced_elements = self._matched_elements[item]

            # Build the slice path representation
            slice_str = self._format_slice(item)
            new_path = self._slice_path + slice_str

            return IDSSlice(
                self.metadata,
                sliced_elements,
                new_path,
            )
        else:
            # Return a single element by index
            return self._matched_elements[int(item)]

    def __getattr__(self, name: str) -> "IDSSlice":
        """Access a child attribute on all matched elements.

        This returns a new IDSSlice containing the child attribute from
        each matched element.

        Args:
            name: Name of the attribute to access

        Returns:
            A new IDSSlice containing the child attribute from each matched element
        """
        # Try to get child metadata if available
        child_metadata = None
        if self.metadata is not None:
            try:
                child_metadata = self.metadata[name]
            except (KeyError, TypeError):
                pass

        # Access the attribute on each element
        child_elements = [getattr(element, name) for element in self]

        # Build the new path including the attribute access
        new_path = self._slice_path + "." + name

        return IDSSlice(
            child_metadata,
            child_elements,
            new_path,
        )

    def __repr__(self) -> str:
        """Build a string representation of this slice."""
        matches_count = len(self._matched_elements)
        match_word = "match" if matches_count == 1 else "matches"
        return f"<IDSSlice ({self._slice_path}, " f"{matches_count} {match_word})>"

    def values(self) -> List[Any]:
        """Extract raw values from elements in this slice.

        For IDSPrimitive elements, this extracts the wrapped value.
        For other element types, returns them as-is.

        This is useful for getting the actual data without the IDS wrapper
        when accessing scalar fields through a slice, without requiring
        explicit looping through the original collection.

        Returns:
            List of raw Python/numpy values or other unwrapped elements

        Examples:
            >>> # Get names from identifiers without looping
            >>> n = edge_profiles.grid_ggd[0].grid_subset[:].identifier.name.values()
            >>> # Result: ["nodes", "edges", "cells"]
            >>>
            >>> # Works with any scalar or array type
            >>> i = edge_profiles.grid_ggd[0].grid_subset[:].identifier.index.values()
            >>> # Result: [1, 2, 5]
            >>>
            >>> # Still works with structures (returns unwrapped)
            >>> ions = profiles[:].ion.values()
            >>> # Result: [IDSStructure(...), IDSStructure(...), ...]
        """
        from imas.ids_primitive import IDSPrimitive

        result = []
        for element in self._matched_elements:
            if isinstance(element, IDSPrimitive):
                # Extract the wrapped value from IDSPrimitive
                result.append(element.value)
            else:
                # Return other types as-is (structures, arrays, etc.)
                result.append(element)
        return result

    def flatten(self, recursive: bool = False) -> "IDSSlice":
        """Flatten nested arrays into a single IDSSlice.

        This method is useful for MATLAB-style matrix-like access.
        It flattens matched elements that are themselves iterable
        (such as IDSStructArray) into a single flat IDSSlice.

        Args:
            recursive: If True, recursively flatten nested IDSSlices.
                      If False (default), only flatten one level.

        Returns:
            New IDSSlice with flattened elements

        Examples:
            >>> # Get all ions from 2 profiles as a flat list
            >>> all_ions = cp.profiles_1d[:2].ion.flatten()
            >>> len(all_ions)  # Number of total ions
            10
            >>> # Iterate over all ions
            >>> for ion in all_ions:
            ...     print(ion.label)

            >>> # Flatten recursively for deeply nested structures
            >>> deeply_nested = obj.level1[:].level2[:].flatten(recursive=True)
        """
        from imas.ids_struct_array import IDSStructArray

        flattened = []

        for element in self._matched_elements:
            if isinstance(element, IDSStructArray):
                # Flatten IDSStructArray elements
                flattened.extend(list(element))
            elif recursive and isinstance(element, IDSSlice):
                # Recursively flatten nested IDSSlices
                flattened.extend(list(element.flatten(recursive=True)))
            else:
                # Keep non-array elements as-is
                flattened.append(element)

        new_path = self._slice_path + ".flatten()"
        return IDSSlice(
            self.metadata,
            flattened,
            new_path,
        )

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
