# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""NetCDF metadata for dimensions and tensorization of IDSs.
"""

from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple

from imas.ids_coordinates import IDSCoordinate
from imas.ids_data_type import IDSDataType
from imas.ids_metadata import IDSMetadata


def _get_aos_label_coordinates(metadata: IDSMetadata) -> List[str]:
    """Extract label coordinates from an Array of Structures metadata."""
    coordinates = []
    for child_name in ("name", "identifier", "label"):
        if child_name in metadata._children:
            label_meta = metadata._children[child_name]
            if label_meta.data_type is IDSDataType.STR and label_meta.ndim == 0:
                coordinates.append(label_meta.path_string.replace("/", "."))
    return coordinates


class NCMetadata:
    """NCMetadata contains additional netCDF metadata for an IDS data structure.

    When constructing an NCMetadata, the complete IDS structure is scanned and all DD
    coordinate information is parsed. This information is used to construct netCDF
    dimension information for all quantities in the IDS.

    Coordinate parsing is done in three phases:

    1.  Traverse the full metadata tree and parse coordinate information for all
        quantities. See ``_parse()`` and ``_parse_dimensions()``.
    2.  Resolve shared dimensions. See ``_resolve_pending()``.
    3.  Tensorize all quantities. See ``_tensorize_dimensions()``.
    """

    def __init__(self, ids_metadata: IDSMetadata) -> None:
        if ids_metadata._parent is not None:
            raise ValueError("Toplevel IDS metadata is required.")

        self.ids_metadata = ids_metadata
        """Metadata of the IDS toplevel that this NC metadata is for."""
        self.time_dimensions: Set[str] = set()
        """Set of all (inhomogeneous) time dimensions."""
        self.dimensions: Dict[str, List[str]] = {}
        """Mapping of paths to dimension names."""
        self.coordinates: Dict[str, List[str]] = {}
        """Mapping of paths to coordinate variable names."""
        self.aos: Dict[str, str] = {}
        """Mapping of paths to their nearest AoS parent."""
        self.paths: List[str] = []
        """List of all paths."""

        # Temporary variables for parsing coordinates
        #   Pending coordinate references
        self._pending = {}  # (path, dimension): (coordinate_path, coordinate_dimension)
        #   Dimensions before tensorization
        self._ut_dims = {}  # path: [dim1, dim2, ...]
        #   Coordinates for each dimension
        self._dim_coordinates = {}  # dimension: [coor1, coor2, ...]
        # Alternative coordinates
        self._alternatives = {}  # path: [alt1, alt2, ...]

        # Parse the whole metadata tree
        self._parse(ids_metadata, None, 0)
        self._merge_alternatives()
        try:
            self._resolve_pending()
        except RecursionError:
            raise RuntimeError(
                "Unable to resolve data dictionary coordinates, does the DD contain"
                " circular coordinate references?"
            ) from None
        self._tensorize_dimensions()
        # Delete temporary variables
        del self._pending, self._ut_dims, self._dim_coordinates, self._alternatives

        # Sanity check:
        assert len(self.dimensions) == len(set(self.dimensions))

        self.time_coordinates: Set[str] = {
            dimension.partition(":")[0] for dimension in self.time_dimensions
        }
        """All coordinate variable names representing (inhomogeneous) time."""

        # Add cache for public API
        self.get_dimensions = lru_cache(maxsize=None)(self.get_dimensions)

    def get_coordinates(self, path: str, homogeneous_time: bool) -> Tuple[str]:
        """Get the coordinates (adhering to CF conventions) for a netCDF variable.

        Args:
            path: Data Dictionary path to the variable, e.g. ``ids_properties/comment``.
            homogeneous_time: Use homogeneous time coordinates. When True,
                ``ids_properties.homogeneous_time`` should be set to ``1``.
        """
        if path not in self.coordinates:
            return ()

        if not homogeneous_time:
            return tuple(self.coordinates[path])

        # Replace inhomogeneous time coordinates with root time:
        return tuple(
            "time" if coord in self.time_coordinates else coord
            for coord in self.coordinates[path]
        )

    def get_dimensions(self, path: str, homogeneous_time: bool) -> Tuple[str]:
        """Get the dimensions for a netCDF variable.

        Args:
            path: Data Dictionary path to the variable, e.g. ``ids_properties/comment``.
            homogeneous_time: Use homogeneous time coordinates. When True,
                ``ids_properties.homogeneous_time`` should be set to ``1``.
        """
        if path not in self.dimensions:
            return ()

        if not homogeneous_time:
            return tuple(self.dimensions[path])

        # Replace inhomogeneous time dimensions with root time:
        return tuple(
            "time" if dim in self.time_dimensions else dim
            for dim in self.dimensions[path]
        )

    def _parse(
        self, metadata: IDSMetadata, parent_aos: Optional[str], aos_level: int
    ) -> None:
        """Recursively parse DD coordinates."""
        for child in metadata._children.values():
            self.paths.append(child.path_string)
            if parent_aos:
                self.aos[child.path_string] = parent_aos

            if child.data_type is IDSDataType.STRUCTURE:
                self._parse(child, parent_aos, aos_level)
            elif child.ndim:
                self._parse_dimensions(child, aos_level)
                if child.data_type is IDSDataType.STRUCT_ARRAY:
                    self._parse(child, child.path_string, aos_level + 1)
            elif parent_aos:
                # These 0D items will have dimensions after tensorizing
                self._ut_dims[child.path_string] = []
            # 0D items without a parent AOS don't have dimensions: we don't store them

    def _parse_dimensions(self, metadata: IDSMetadata, aos_level: int) -> None:
        """Parse dimensions and auxiliary coordinates from DD coordinate metadata.

        DD coordinates come in different flavours (see also
        :mod:`imas.ids_coordinates`), which we handle in this function:

        1.  Coordinate is an index.

            This is expressed in the Data Dictionary as ``coordinateX=1...N``, where
            ``N`` can be an integer indicating the exact size of the dimension, or a
            literal ``N`` when the dimension is unbounded.

            Such an index will become its own netCDF dimension.

        2.  Coordinate shares a dimension with another variable, but there is no
            explicit coordinate variable in the DD.

            This is expressed in the Data Dictionary as ``coordinateX=1...N`` (like in
            case 1), but in addition there is an attribute ``coordinateX_same_as=...``
            which indicates the variable it shares its dimension with.

        3.  Coordinate refers to another quantity in the DD.

            This is expressed in the Data Dictionary as ``coordinateX=quantity`` which
            indicates the variable that is the coordinate. Note that a time coordinate
            is treated specially, see below.

            a.  Starting in Data Dictionary version 4.0.0, the coordinate quantity can
                indicate that there are alternatives for itself. This is expressed as
                ``alternative_coordinate1=quantity1;quantity2;...``.

        4.  Coordinate refers to multiple other quantities in the DD.

            This is expressed in the Data Dictionary as ``coordinateX=quantity1 OR
            quantity2 [OR ...]``.

        Notes:

        -   It is assumed that there are no circular coordinate references, i.e. no two
            quantities in the Data Dictionary point to eachother as a coordinate.
        -   Time dimensions and coordinate names are recorded separately. When using
            homogeneous_time, all time coordinates point to the root ``time`` quantity
            instead of the quantity recorded in the coordinate properties.
        -   Error bars of quantities (quantities whose name ends in ``_error_upper`` or
            ``_error_lower``) always share the dimensions of the quantities they belong
            to.
        """
        path = metadata.path_string
        # Handle errorbar quantities
        if path.endswith("_error_upper") or path.endswith("_error_lower"):
            self._ut_dims[path] = [None] * metadata.ndim
            # Note: only works because _error_upper/_error_lower both have length 12
            coordinate_path = path[:-12]
            for i in range(metadata.ndim):
                self._pending[(path, i)] = (coordinate_path, i)
            return

        # Handle regular nodes
        dimensions = []
        for i, coord in enumerate(metadata.coordinates):
            dim_name = None
            if coord.references:
                # ------ CASE 3 or 4: refers to other quantities ------
                if metadata.path.is_ancestor_of(coord.references[0]):
                    # Coordinate is inside this AoS (and must be 0D): create dimension
                    # E.g. core_profiles IDS: profiles_1d -> profiles_1d/time
                    dim_name = ".".join(coord.references[0].parts)
                    is_time_dimension = coord.is_time_coordinate
                    coordinates = [dim_name]

                else:
                    main_coord_path = self._handle_alternatives(coord)
                    self._pending[(path, i)] = (main_coord_path, 0)

            else:
                same_as = metadata.coordinates_same_as[i]
                if same_as.references:
                    # ------ CASE 2: coordinate is same as another ------
                    # There currently is no case with alternative coordinate_same_as,
                    # if this ever changes we need to think how to handle this...
                    assert len(same_as.references) == 1
                    main_coord_path = self._handle_alternatives(same_as)
                    self._pending[(path, i)] = (main_coord_path, i)

                else:
                    # ------ CASE 1: coordinate is an index ------
                    # Create a new dimension
                    dim_name = path.replace("/", ".")
                    coordinates = [dim_name]
                    if (
                        aos_level + metadata.ndim != 1
                        or metadata.data_type is IDSDataType.STRUCT_ARRAY
                    ):
                        # This variable is >1D after tensorization, or it is an AoS,
                        # so we cannot use our path as dimension name: add suffix
                        suffix = "ijklmn"[i]
                        dim_name = f"{dim_name}:{suffix}"
                    is_time_dimension = metadata.name == "time"
                    if metadata.data_type is IDSDataType.STRUCT_ARRAY:
                        # Check if name/identifier/label exists
                        coordinates = _get_aos_label_coordinates(metadata)

            dimensions.append(dim_name)
            if dim_name is not None:
                if is_time_dimension:
                    # Record time dimension
                    self.time_dimensions.add(dim_name)
                # Record coordinates for this dimension
                self._dim_coordinates[dim_name] = coordinates

        # Handle DDv4 alternative coordinates
        if metadata.alternative_coordinates:
            # Record for _merge_alternatives()
            self._alternatives.setdefault(metadata.path_string, []).extend(
                "/".join(ref.parts) for ref in metadata.alternative_coordinates
            )
            # Add alternatives to the coordinates for this dimension
            self._dim_coordinates[dim_name].extend(
                ".".join(ref.parts) for ref in metadata.alternative_coordinates
            )

        # Store untensorized dimensions
        self._ut_dims[path] = dimensions

    def _handle_alternatives(self, coord: IDSCoordinate) -> str:
        """Handle alternative coordinates. Return main coordinate path."""
        main, *others = ["/".join(ref.parts) for ref in coord.references]
        if others:
            if main in self._alternatives:
                self._alternatives[main].extend(others)
            else:
                self._alternatives[main] = others
        return main

    def _merge_alternatives(self) -> None:
        """Merge all alternative coordinates to use the same dimension."""
        for path, alternatives in self._alternatives.items():
            # Alternatives are only applicable for 1D nodes
            assert len(self._ut_dims[path]) == 1
            for alternative in alternatives:
                # Alternatives are only applicable for 1D nodes
                assert len(self._ut_dims[alternative]) == 1
                if self._ut_dims[alternative][0] is None:
                    assert self._pending[(alternative, 0)] == (path, 0)
                else:
                    self._ut_dims[alternative][0] = None
                    self._pending[(alternative, 0)] = (path, 0)

            # Update coordinates
            dim_name = self._ut_dims[path][0]
            alternative_coordinates = [alt.replace("/", ".") for alt in alternatives]
            # Only add items not already present
            coordinates = self._dim_coordinates[dim_name]
            for alt in alternative_coordinates:
                if alt not in coordinates:
                    coordinates.append(alt)

    def _resolve_pending(self):
        """Resolve all pending dimension references."""
        pending_items = self._pending.items()
        self._pending = {}

        for (path, dimension), (coor_path, coor_dimension) in pending_items:
            dim = self._ut_dims[coor_path][coor_dimension]
            if dim is None:
                # We refer to a (still) unresolved coordinate, put back in the queue:
                self._pending[(path, dimension)] = (coor_path, coor_dimension)
            else:
                # Reference is resolved:
                self._ut_dims[path][dimension] = dim

        # If we have any pending left, try to resolve them again.
        # Note: if there are circular references we cannot resolve them, and this will
        # at some point raise a RecursionError. This error is caught in __init__() and a
        # more meaningful exception is raised instead.
        if self._pending:
            self._resolve_pending()

    def _tensorize_dimensions(self):
        """Create the final tensorized data structures.

        This prepends all dimensions (coordinates) with the dimensions (coordinates) of
        their ancestor Array of Structures.
        """
        for path in self._ut_dims:
            aos_dims = coordinates = []
            aos = self.aos.get(path)
            if aos is not None:
                # Note: by construction of self._ut_dims, we know that ancestor AOSs are
                # always handled before their children. self.dimensions[aos] must
                # therefore exist:
                aos_dims = self.dimensions[aos]
                coordinates = self.coordinates.get(aos, []).copy()
            self.dimensions[path] = aos_dims + self._ut_dims[path]

            # Set auxiliary coordinates
            metadata = self.ids_metadata[path]
            for coord, dim_name in zip(metadata.coordinates, self._ut_dims[path]):
                if coord.references:
                    coordinates.extend(self._dim_coordinates[dim_name])

            if metadata.data_type is IDSDataType.STRUCT_ARRAY:
                # Check if name/identifier/label exists
                coordinates.extend(_get_aos_label_coordinates(metadata))
            if coordinates:
                self.coordinates[path] = coordinates
