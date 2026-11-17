# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Tensorization logic to convert IDSs to netCDF files and/or xarray Datasets."""

from collections import deque
from typing import List, Tuple, Dict

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
        self.homogeneous_time = bool(
            ids.ids_properties.homogeneous_time == IDS_TIME_MODE_HOMOGENEOUS
        )
        """True iff the IDS time mode is homogeneous."""
        self.shapes = {}
        """Map of IDS paths to data shape arrays."""

    def get_dimensions(self, path: str) -> Tuple[str, ...]:
        """Get the dimensions for a netCDF variable.

        Args:
            path: Data Dictionary path to the variable, e.g. ``ids_properties/comment``.
        """
        return self.ncmeta.get_dimensions(path, self.homogeneous_time)

    def get_shape_dimensions(self, path: str) -> Tuple[str, ...]:
        """Get dimensions names for shape array of the tensorized variable"""
        ndim = self.ids.metadata[path].ndim
        return self.get_dimensions(self.ncmeta.aos.get(path, "")) + (f"{ndim}D",)

    def include_coordinate_paths(self) -> None:
        """Append all paths that are coordinates of self.paths_to_tensorize"""
        # Use a queue so we can also take coordinates of coordinates into account
        queue = deque(self.paths_to_tensorize)
        # Include all parent AoS as well:
        for path in self.paths_to_tensorize:
            while path:
                path, _, _ = path.rpartition("/")
                if self.get_dimensions(path):
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
            dimensions = self.get_dimensions(path)
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
        for path, nodes_dict in self.filled_data.items():
            metadata = self.ids.metadata[path]
            # Structures don't have a size
            if metadata.data_type is IDSDataType.STRUCTURE:
                continue
            ndim = metadata.ndim
            dimensions = self.get_dimensions(path)

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
                aos_dims = self.get_dimensions(self.ncmeta.aos[path])
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

    def get_attributes(self, path: str, fillvals: dict) -> Dict[str, str]:
        """Get metadata attributes of the tensorized variable"""
        metadata = self.ids.metadata[path]
        var_name = path.replace("/", ".")

        assert metadata.documentation is not None
        attrs = {"documentation": metadata.documentation}
        if metadata.units:
            attrs["units"] = metadata.units

        ancillary_variables = " ".join(
            error_var
            for error_var in [f"{var_name}_error_upper", f"{var_name}_error_lower"]
            if error_var in self.filled_variables
        )
        if ancillary_variables:
            attrs["ancillary_variables"] = ancillary_variables

        if metadata.data_type is not IDSDataType.STRUCT_ARRAY:
            coordinates = self.filter_coordinates(path)
            if coordinates:
                attrs["coordinates"] = coordinates

        # Sparsity
        if path in self.shapes:
            if not metadata.ndim:
                # Doesn't need a :shape array
                attrs["sparse"] = (
                    "Sparse data, missing data is filled with _FillValue"
                    f" ({fillvals[metadata.data_type]})"
                )
            else:
                attrs["sparse"] = (
                    f"Sparse data, data shapes are stored in {var_name}:shape"
                )

        return attrs

    def get_shape_attributes(self, var_name: str) -> Dict[str, str]:
        """Get attributes of the :shape variable corresponding to var_name"""
        doc_indices = ",".join(chr(ord("i") + i) for i in range(3))
        documentation = (
            f"Shape information for {var_name}.\n"
            f"{var_name}:shape[{doc_indices},:] describes the shape of filled "
            f"data of {var_name}[{doc_indices},...]. Data outside this "
            "shape is unset (i.e. filled with _Fillvalue)."
        )
        return {"documentation": documentation}

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
        dimensions = self.get_dimensions(path)
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

    def _recursively_convert_to_list(
        self, path: str, inactive_index: Tuple, shape: Tuple, i_dim: int
    ):
        entry = []
        for index in range(shape[i_dim]):
            new_index = inactive_index + (index,)
            if i_dim == len(shape) - 1:
                entry.append(self.filled_data[path][new_index].value)
            else:
                entry.append(
                    self._recursively_convert_to_list(path, new_index, shape, i_dim + 1)
                )
        return entry

    def awkward_tensorize(self, path: str):
        """
        Tensorizes the data at the given path with the specified fill value.

        Args:
            path: The path to the data in the IDS.

        Returns:
            A tensor filled with the data from the specified path.
        """
        if not self.filled_data[path]:
            return []
        hdf5_dim = len(next(iter(self.filled_data[path])))

        if hdf5_dim == 0:
            return self.filled_data[path][()].value

        if path in self.shapes:
            shape = self.shapes[path].shape[:hdf5_dim]
        else:
            dimensions = self.ncmeta.get_dimensions(path, self.homogeneous_time)
            full_shape = tuple(self.dimension_size[dim] for dim in dimensions)
            # Get the split between HDF5 indices and stored matrices
            # i.e. equilibrium.time_slice.profiles_2d <-> psi
            shape = full_shape[:hdf5_dim]

        return self._recursively_convert_to_list(path, tuple(), shape, 0)
