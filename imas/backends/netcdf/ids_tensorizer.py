# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Tensorization logic to convert IDSs to netCDF files and/or xarray Datasets."""

from collections import deque
from typing import List

import numpy

from imas.backends.netcdf.iterators import indexed_tree_iter
from imas.backends.netcdf.nc_metadata import NCMetadata
from imas.ids_data_type import IDSDataType
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS
from imas.ids_toplevel import IDSToplevel

dtypes = {
    IDSDataType.INT: numpy.dtype(numpy.int32),
    IDSDataType.STR: str,
    IDSDataType.FLT: numpy.dtype(numpy.float64),
    IDSDataType.CPX: numpy.dtype(numpy.complex128),
}
SHAPE_DTYPE = numpy.int32


class IDSTensorizer:
    """Common functionality for tensorizing IDSs. Used in IDS2NC and util.to_xarray."""

    def __init__(self, ids: IDSToplevel, paths_to_tensorize: List[str]) -> None:
        """Initialize IDSTensorizer.

        Args:
            ids: IDSToplevel to store in the netCDF group
            paths_to_tensorize: Restrict tensorization to the provided paths. If an
                empty list is provided, all filled quantities in the IDS will be
                tensorized.
        """
        self.ids = ids
        """IDS to tensorize."""
        self.paths_to_tensorize = paths_to_tensorize
        """List of paths to tensorize"""

        self.ncmeta = NCMetadata(ids.metadata)
        """NetCDF related metadata."""
        self.dimension_size = {}
        """Map dimension name to its size."""
        self.filled_data = {}
        """Map of IDS paths to filled data nodes."""
        self.filled_variables = set()
        """Set of filled IDS variables"""
        self.homogeneous_time = (
            ids.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS
        )
        """True iff the IDS time mode is homogeneous."""
        self.shapes = {}
        """Map of IDS paths to data shape arrays."""

    def include_coordinate_paths(self) -> None:
        """Append all paths that are coordinates of self.paths_to_tensorize"""
        # Use a queue so we can also take coordinates of coordinates into account
        queue = deque(self.paths_to_tensorize)
        # Include all parent AoS as well:
        for path in self.paths_to_tensorize:
            while path:
                path, _, _ = path.rpartition("/")
                if self.ncmeta.get_dimensions(path, self.homogeneous_time):
                    queue.append(path)

        self.paths_to_tensorize = []
        while queue:
            path = queue.popleft()
            if path in self.paths_to_tensorize:
                continue  # already processed
            self.paths_to_tensorize.append(path)
            for coordinate in self.ncmeta.get_coordinates(path, self.homogeneous_time):
                queue.append(coordinate.replace(".", "/"))

    def collect_filled_data(self) -> None:
        """Collect all filled data in the IDS and determine dimension sizes.

        Results are stored in :attr:`filled_data` and :attr:`dimension_size`.
        """
        # Initialize dictionary with all paths that could exist in this IDS
        filled_data = {path: {} for path in self.ncmeta.paths}
        dimension_size = {}
        get_dimensions = self.ncmeta.get_dimensions

        if self.paths_to_tensorize:
            # Restrict tensorization to provided paths
            iterator = (
                item
                for path in self.paths_to_tensorize
                for item in indexed_tree_iter(self.ids, self.ids.metadata[path])
                if item[1].has_value  # Skip nodes without value set
            )
        else:
            # Tensorize all non-empty nodes
            iterator = indexed_tree_iter(self.ids)

        for aos_index, node in iterator:
            path = node.metadata.path_string
            filled_data[path][aos_index] = node
            ndim = node.metadata.ndim
            if not ndim:
                continue
            dimensions = get_dimensions(path, self.homogeneous_time)
            # We're only interested in the non-tensorized dimensions: [-ndim:]
            for dim_name, size in zip(dimensions[-ndim:], node.shape):
                dimension_size[dim_name] = max(dimension_size.get(dim_name, 0), size)

        # Remove paths without data
        self.filled_data = {path: data for path, data in filled_data.items() if data}
        self.filled_variables = {path.replace("/", ".") for path in self.filled_data}
        # Store dimension sizes
        self.dimension_size = dimension_size

    def determine_data_shapes(self) -> None:
        """Determine tensorized data shapes and sparsity, save in :attr:`shapes`."""
        get_dimensions = self.ncmeta.get_dimensions

        for path, nodes_dict in self.filled_data.items():
            metadata = self.ids.metadata[path]
            # Structures don't have a size
            if metadata.data_type is IDSDataType.STRUCTURE:
                continue
            ndim = metadata.ndim
            dimensions = get_dimensions(path, self.homogeneous_time)

            # node shape if it is completely filled
            full_shape = tuple(self.dimension_size[dim] for dim in dimensions[-ndim:])

            if len(dimensions) == ndim:
                # Data at this path is not tensorized
                node = nodes_dict[()]
                sparse = node.shape != full_shape
                if sparse:
                    shapes = numpy.array(node.shape, dtype=SHAPE_DTYPE)

            else:
                # Data is tensorized, determine if it is homogeneously shaped
                aos_dims = get_dimensions(self.ncmeta.aos[path], self.homogeneous_time)
                shapes_shape = [self.dimension_size[dim] for dim in aos_dims]
                if ndim:
                    shapes_shape.append(ndim)
                shapes = numpy.zeros(shapes_shape, dtype=SHAPE_DTYPE)

                if ndim:  # ND types have a shape
                    for aos_coords, node in nodes_dict.items():
                        shapes[aos_coords] = node.shape
                    sparse = not numpy.array_equiv(shapes, full_shape)

                else:  # 0D types don't have a shape
                    for aos_coords in nodes_dict.keys():
                        shapes[aos_coords] = 1
                    sparse = not shapes.all()
                    shapes = None

            if sparse:
                self.shapes[path] = shapes
                if ndim:
                    # Ensure there is a pseudo-dimension f"{ndim}D" for shapes variable
                    self.dimension_size[f"{ndim}D"] = ndim

    def filter_coordinates(self, path: str) -> str:
        """Filter the coordinates list from NCMetadata to filled variables only."""
        return " ".join(
            coordinate
            for coordinate in self.ncmeta.get_coordinates(path, self.homogeneous_time)
            if coordinate in self.filled_variables
        )

    def tensorize(self, path, fillvalue):
        """
        Tensorizes the data at the given path with the specified fill value.

        Args:
            path: The path to the data in the IDS.
            fillvalue: The value to fill the tensor with. Can be of any type,
                             including strings.

        Returns:
            A tensor filled with the data from the specified path.
        """
        dimensions = self.ncmeta.get_dimensions(path, self.homogeneous_time)
        shape = tuple(self.dimension_size[dim] for dim in dimensions)

        # TODO: depending on the data, tmp_var may be HUGE, we may need a more
        # efficient assignment algorithm for large and/or irregular data
        tmp_var = numpy.full(shape, fillvalue)
        if isinstance(fillvalue, str):
            tmp_var = numpy.asarray(tmp_var, dtype=object)

        shapes = self.shapes.get(path)
        nodes_dict = self.filled_data[path]

        # Fill tmp_var
        if shapes is None:
            # Data is not sparse, so we can assign to the aos_coords
            for aos_coords, node in nodes_dict.items():
                tmp_var[aos_coords] = node.value
        else:
            # Data is sparse, so we must select a slice
            for aos_coords, node in nodes_dict.items():
                tmp_var[aos_coords + tuple(map(slice, node.shape))] = node.value

        return tmp_var
