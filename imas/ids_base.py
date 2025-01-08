# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Base class for all IDS nodes.
"""

import logging
from typing import TYPE_CHECKING, Optional, Type

from imas.exception import ValidationError
from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT
from imas.ids_metadata import IDSMetadata

if TYPE_CHECKING:
    from imas.ids_toplevel import IDSToplevel

logger = logging.getLogger(__name__)


class IDSBase:
    """The base class which unifies properties of structure, struct_array, toplevel
    and data nodes."""

    # Since a lot of IDSBase objects are constructed, the overhead of implementing
    # __init__() in this class is quite significant: 5-10% runtime in some
    # cases for a DBEntry.get()!
    # The following attributes should be set in a derived class's __init__():
    __slots__ = ()  # _parent and metadata should be slots in derived classes as well!
    _parent: "IDSBase"
    """Parent object of this IDS node"""
    metadata: IDSMetadata
    """Metadata of this IDS node"""

    # _lazy is defined on all derived classes
    _lazy: bool
    """True iff this IDS lazy-loads its data"""

    @property
    def _time_mode(self) -> int:
        """Retrieve the time mode from `/ids_properties/homogeneous_time`"""
        return self._parent._time_mode

    @property
    def _dd_parent(self) -> "IDSBase":
        """Return the DD parent element

        Usually this is the same as the _parent element, but for IDSStructArray
        structure sub-elements, this will return the parent of the IDSStructArray.

        Examples:
            - `ids.ids_properties.provenance._dd_parent` is `ids.ids_properties`
            - `ids.ids_properties.provenance[0]._dd_parent` is also `ids.ids_properties`
        """
        return self._parent

    @property
    def _path(self) -> str:
        """Build relative path from the toplevel to the node

        Caution:
            Determining the path is relatively expensive in large, nested Arrays of
            Structures: the calculation of the index suffix is O(N) in the size of the
            AoS.

            Usage of _path is (and should remain) limited to "interactive" use cases
            (like in :mod:`imas.util` and ``__repr__``) or when reporting errors.

        Examples:
            - ``ids.ids_properties.creation_data._path`` is
              ``"ids_properties/creation_date"``
            - ``gyrokinetics.wavevector[0].radial_component_norm._path`` is
              ``"wavevector[0]/radial_component_norm"``
        """
        from imas.ids_struct_array import IDSStructArray

        parent_path = self._parent._path
        my_path = self.metadata.name
        if isinstance(self._parent, IDSStructArray):
            for index, item in enumerate(self._parent):
                if item is self:
                    break
            else:
                # This happens when we ask the path of a struct_array
                # child that does not have a proper parent anymore
                # E.g. a resize
                logger.warning(
                    "Link to parent of %s broken. Cannot reconstruct index", my_path
                )
                index = "?"
            my_path = f"{parent_path}[{index}]"
        elif parent_path != "":
            # If we are not an IDSStructArray, we have no indexable children.
            my_path = parent_path + "/" + my_path
        return my_path

    @property
    def _version(self):
        """Return the data dictionary version of this in-memory structure."""
        return self._parent._version

    def _build_repr_start(self) -> str:
        """Build the start of the string derived classes need for their repr.

        All derived classes need to represent the IDS they are part of,
        and thus have a common string to start with. We collect that common logic here.
        """
        my_repr = f"<{type(self).__name__}"
        my_repr += f" (IDS:{self._toplevel.metadata.name},"
        my_repr += f" {self._path}"
        return my_repr

    @property
    def _toplevel(self) -> "IDSToplevel":
        """Return the toplevel instance this node belongs to"""
        return self._parent._toplevel

    def _validate(self) -> None:
        """Actual implementation of validation logic.

        See also:
            :py:meth:`imas.ids_toplevel.IDSToplevel.validate`.

        Args:
            aos_indices: index_name -> index, e.g. {"i1": 1, "itime": 0}, for all parent
                array of structures.
        """
        if self.metadata.type.is_dynamic and self.has_value:
            if self._time_mode == IDS_TIME_MODE_INDEPENDENT:
                raise ValidationError(
                    f"Dynamic variable {self.metadata.path} is allocated, but time "
                    "mode is IDS_TIME_MODE_INDEPENDENT."
                )


class IDSDoc:
    """Helper class to show DD documentation on IDS objects.

    This object implements the descriptor protocol, see:
    https://docs.python.org/3/howto/descriptor.html.
    """

    def __init__(self, original_doc: str) -> None:
        self.original_doc = original_doc

    def __get__(
        self, instance: Optional[IDSBase], owner: Optional[Type[IDSBase]] = None
    ) -> str:
        if instance is None:
            return self.original_doc  # class-level
        return instance.metadata.documentation or self.original_doc  # instance-level
