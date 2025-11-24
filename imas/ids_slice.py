# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""IDSSlice represents a collection of IDS nodes matching a slice expression.

This module provides the IDSSlice class, which enables slicing of arrays of
structures while maintaining the hierarchy and allowing further operations on
the resulting collection.
"""

import logging
from typing import Any, Iterator, List, Optional, Union

from imas.ids_metadata import IDSMetadata

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

    __slots__ = ["metadata", "_matched_elements", "_slice_path"]

    def __init__(
        self,
        metadata: Optional[IDSMetadata],
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
                sliced_elements = []
                for array in self._matched_elements:
                    sliced_elements.extend(list(array[item]))

                slice_str = self._format_slice(item)
                new_path = self._slice_path + slice_str

                return IDSSlice(
                    self.metadata,
                    sliced_elements,
                    new_path,
                )
            else:
                indexed_elements = []
                for array in self._matched_elements:
                    indexed_elements.append(array[item])

                new_path = self._slice_path + f"[{item}]"

                return IDSSlice(
                    self.metadata,
                    indexed_elements,
                    new_path,
                )
        else:
            if isinstance(item, slice):
                sliced_elements = self._matched_elements[item]
                slice_str = self._format_slice(item)
                new_path = self._slice_path + slice_str

                return IDSSlice(
                    self.metadata,
                    sliced_elements,
                    new_path,
                )
            else:
                return self._matched_elements[int(item)]

    def __getattr__(self, name: str) -> "IDSSlice":
        """Access a child node on all matched elements.

        This returns a new IDSSlice containing the child node from
        each matched element.

        Args:
            name: Name of the node to access

        Returns:
            A new IDSSlice containing the child node from each matched element
        """
        if not self._matched_elements:
            raise IndexError(
                f"Cannot access node '{name}' on empty slice with 0 elements"
            )

        child_metadata = None
        if self.metadata is not None:
            try:
                child_metadata = self.metadata[name]
            except (KeyError, TypeError):
                pass

        child_elements = [getattr(element, name) for element in self]
        new_path = self._slice_path + "." + name

        return IDSSlice(
            child_metadata,
            child_elements,
            new_path,
        )

    def __repr__(self) -> str:
        """Build a string representation of this slice."""
        matches_count = len(self._matched_elements)
        match_word = "item" if matches_count == 1 else "items"

        array_name = self.metadata.name if self.metadata else ""
        ids_name = ""
        if self._matched_elements:
            elem = self._matched_elements[0]
            if hasattr(elem, "_toplevel") and hasattr(elem._toplevel, "metadata"):
                ids_name = elem._toplevel.metadata.name
        ids_prefix = f"IDS:{ids_name}, " if ids_name else ""

        return (
            f"<IDSSlice ({ids_prefix}{array_name} with {matches_count} {match_word})>"
        )

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
                result.append(element.value)
            else:
                result.append(element)
        return result

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
