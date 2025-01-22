# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""IDS StructArray represents an Array of Structures in the IDS tree.
"""

import logging
from copy import deepcopy
from typing import Optional, Tuple

from xxhash import xxh3_64

from imas.backends.imas_core.al_context import LazyALArrayStructContext
from imas.ids_base import IDSBase, IDSDoc
from imas.ids_coordinates import IDSCoordinates
from imas.ids_identifiers import IDSIdentifier
from imas.ids_metadata import IDSMetadata

logger = logging.getLogger(__name__)


class IDSStructArray(IDSBase):
    """IDS array of structures (AoS) node

    Represents a node in the IDS tree. Does not itself contain data,
    but contains references to IDSStructures
    """

    __doc__ = IDSDoc(__doc__)
    __slots__ = ["_parent", "_lazy", "metadata", "value", "_lazy_ctx"]

    def __init__(self, parent: IDSBase, metadata: IDSMetadata):
        """Initialize IDSStructArray from XML specification

        Args:
            parent: Parent structure. Can be anything, but at database write
                time should be something with a path attribute
            metadata: IDSMetadata describing the structure of the IDS
        """
        self._parent = parent
        self._lazy = parent._lazy
        self.metadata = metadata

        # Initialize with an 0-length list or None when lazy loading
        self.value = None if self._lazy else []
        """"""

        # Lazy loading context, only applicable when self._lazy is True
        # When lazy loading, all items in self.value are None until they are requested
        self._lazy_ctx: Optional[LazyALArrayStructContext] = None

    @property
    def coordinates(self):
        """Coordinates of this array of structures."""
        return IDSCoordinates(self)

    def __deepcopy__(self, memo):
        copy = self.__class__(self._parent, self.metadata)
        for value in self.value:
            value_copy = deepcopy(value, memo)
            value_copy._parent = copy
            copy.value.append(value_copy)
        return copy

    def __eq__(self, other) -> bool:
        if self is other:
            return True
        if not isinstance(other, IDSStructArray):
            return False
        # Equal if same size and all contained structures are the same
        return len(self) == len(other) and all(a == b for a, b in zip(self, other))

    def _set_lazy_context(self, ctx: LazyALArrayStructContext) -> None:
        """Called by DBEntry during a lazy get/get_slice.

        Set the context that we can use for retrieving our size and children.
        """
        self._lazy_ctx = ctx

    def _load(self, item: Optional[int]) -> None:
        """When lazy loading, ensure that the requested item is loaded.

        Args:
            item: index of the item to load. When None, just ensure that our size is
                loaded from the lowlevel.
        """
        assert self._lazy
        if self.value is not None:  # We already loaded our size
            if item is None:
                return
            if self.value[item] is not None:
                return  # item is already loaded
        # Load requested data from the backend
        if self.value is None:
            if self._lazy_ctx is None:
                # Lazy context can be None when:
                # 1. The element does not exist in the on-disk DD version
                # 2. The element exists, but changed type compared to the on-disk DD
                # In both cases we just report that we're empty
                self.value = []
            else:
                ctx = self._lazy_ctx.get_context()
                self.value = [None] * ctx.size

        if item is not None:
            if item < 0:
                item += len(self)
            if item < 0 or item >= len(self):
                raise IndexError("list index out of range")
            # Create the requested item
            from imas.ids_structure import IDSStructure

            element = self.value[item] = IDSStructure(self, self.metadata)
            element._set_lazy_context(self._lazy_ctx.iterate_to_index(item))

    @property
    def _element_structure(self):
        """Prepare an element structure JIT"""
        from imas.ids_structure import IDSStructure

        struct = IDSStructure(self, self.metadata)
        return struct

    def __getitem__(self, item):
        # value is a list, so the given item should be convertable to integer
        # TODO: perhaps we should allow slices as well?
        list_idx = int(item)
        if self._lazy:
            self._load(item)
        return self.value[list_idx]

    def __setitem__(self, item, value):
        # value is a list, so the given item should be convertable to integer
        # TODO: perhaps we should allow slices as well?
        if self._lazy:
            raise ValueError("Lazy-loaded IDSs are read-only.")
        list_idx = int(item)
        if isinstance(value, (IDSIdentifier, str, int)):
            self.value[list_idx]._assign_identifier(value)
        else:  # FIXME: check if value is of the correct class
            self.value[list_idx] = value

    def __len__(self) -> int:
        if self._lazy:
            self._load(None)
        return len(self.value)

    @property
    def shape(self) -> Tuple[int]:
        """Get the shape of the contained data.

        This will always return a tuple: ``(len(self), )``.
        """
        if self._lazy:
            self._load(None)
        return (len(self.value),)

    def append(self, elt):
        """Append elements to the end of the array of structures.

        Args:
            elt: IDS structure, or list of IDS structures, to append to this array
        """
        if self._lazy:
            raise ValueError("Lazy-loaded IDSs are read-only.")
        if not isinstance(elt, list):
            elements = [elt]
        else:
            elements = elt
        for e in elements:
            # Just blindly append for now
            # TODO: Maybe check if user is not trying to append weird elements
            e._parent = self
            self.value.append(e)

    def __repr__(self):
        return f"{self._build_repr_start()} with {len(self)} items)>"

    def resize(self, nbelt: int, keep: bool = False):
        """Resize an array of structures.

        Args:
            nbelt: The number of elements for the targeted array of structure,
                which can be smaller or bigger than the size of the current
                array if it already exists.
            keep: Specifies if the targeted array of structure should keep
                existing data in remaining elements after resizing it.
        """
        if self._lazy:
            raise ValueError("Lazy-loaded IDSs are read-only.")
        if nbelt < 0:
            raise ValueError(f"Invalid size {nbelt}: size may not be negative")
        if not keep:
            self.value = []
        cur = len(self.value)
        if nbelt > cur:
            # Create new structures to fill this AoS with
            from imas.ids_structure import IDSStructure

            new_els = [IDSStructure(self, self.metadata) for _ in range(nbelt - cur)]
            if cur:
                self.value.extend(new_els)
            else:
                self.value = new_els
        elif nbelt < cur:
            self.value = self.value[:nbelt]
        else:  # nbelt == cur
            pass  # nothing to do, already correct size

    @property
    def has_value(self) -> bool:
        """True if this struct-array has nonzero size"""
        # Note self.__len__ will lazy load our size if needed
        return len(self) > 0

    @property
    def size(self) -> int:
        """Get the number of elements in this array"""
        return len(self)

    def _validate(self) -> None:
        # Common validation logic
        super()._validate()
        # IDSStructArray specific: validate coordinates and child nodes
        if self.has_value:
            self.coordinates._validate()
            for child in self:
                child._validate()

    def _xxhash(self) -> bytes:
        hsh = xxh3_64(len(self).to_bytes(8, "little"))
        for s in self:
            hsh.update(s._xxhash())
        return hsh.digest()
