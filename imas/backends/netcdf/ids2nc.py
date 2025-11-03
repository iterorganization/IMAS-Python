# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""NetCDF IO support for IMAS-Python. Requires [netcdf] extra dependencies."""

import netCDF4
from packaging import version

from imas.backends.netcdf.ids_tensorizer import SHAPE_DTYPE, IDSTensorizer, dtypes
from imas.exception import InvalidNetCDFEntry
from imas.ids_data_type import IDSDataType
from imas.ids_toplevel import IDSToplevel

default_fillvals = {
    IDSDataType.INT: netCDF4.default_fillvals["i4"],
    IDSDataType.STR: "",
    IDSDataType.FLT: netCDF4.default_fillvals["f8"],
    IDSDataType.CPX: netCDF4.default_fillvals["f8"] * (1 + 1j),
}


class IDS2NC(IDSTensorizer):
    """Class responsible for storing an IDS to a NetCDF file."""

    def __init__(self, ids: IDSToplevel, group: netCDF4.Group) -> None:
        """Initialize IDS2NC converter.

        Args:
            ids: IDSToplevel to store in the netCDF group
            group: Empty netCDF group to store the IDS in.
        """
        super().__init__(ids, [])  # pass empty list: tensorize full IDS
        self.group = group
        """NetCDF Group to store the IDS in."""

    def run(self) -> None:
        """Store the IDS in the NetCDF group."""
        self.collect_filled_data()
        self.determine_data_shapes()
        self.create_dimensions()
        self.create_variables()
        self.store_data()

    def create_dimensions(self) -> None:
        """Create netCDF dimensions."""
        for dimension, size in self.dimension_size.items():
            self.group.createDimension(dimension, size)

    def create_variables(self) -> None:
        """Create netCDF variables."""
        get_dimensions = self.ncmeta.get_dimensions
        for path in self.filled_data:
            metadata = self.ids.metadata[path]
            var_name = path.replace("/", ".")

            if metadata.data_type in (IDSDataType.STRUCTURE, IDSDataType.STRUCT_ARRAY):
                # Create a 0D dummy variable for metadata
                var = self.group.createVariable(var_name, "S1", ())

            else:
                dtype = dtypes[metadata.data_type]
                if (
                    version.parse(netCDF4.__version__) < version.parse("1.7.0")
                    and dtype is dtypes[IDSDataType.CPX]
                ):
                    raise InvalidNetCDFEntry(
                        f"Found complex data in {var_name}, NetCDF 1.7.0 or"
                        f" later is required for complex data types"
                    )
                kwargs = {}
                if dtype is not str:  # Enable compression:
                    if version.parse(netCDF4.__version__) > version.parse("1.4.1"):
                        kwargs.update(compression="zlib", complevel=1)
                    else:
                        kwargs.update(zlib=True, complevel=1)
                if dtype is not dtypes[IDSDataType.CPX]:  # Set fillvalue
                    kwargs.update(fill_value=default_fillvals[metadata.data_type])
                # Create variable
                dimensions = get_dimensions(path, self.homogeneous_time)
                var = self.group.createVariable(var_name, dtype, dimensions, **kwargs)

            # Fill metadata attributes
            var.documentation = metadata.documentation
            if metadata.units:
                var.units = metadata.units

            ancillary_variables = " ".join(
                error_var
                for error_var in [f"{var_name}_error_upper", f"{var_name}_error_lower"]
                if error_var in self.filled_variables
            )
            if ancillary_variables:
                var.ancillary_variables = ancillary_variables

            if metadata.data_type is not IDSDataType.STRUCT_ARRAY:
                coordinates = self.filter_coordinates(path)
                if coordinates:
                    var.coordinates = coordinates

            # Sparsity and :shape array
            if path in self.shapes:
                if not metadata.ndim:
                    # Doesn't need a :shape array:
                    var.sparse = "Sparse data, missing data is filled with _FillValue"
                    var.sparse += f" ({default_fillvals[metadata.data_type]})"

                else:
                    shape_name = f"{var_name}:shape"
                    var.sparse = f"Sparse data, data shapes are stored in {shape_name}"

                    # Create variable to store data shape
                    dimensions = get_dimensions(
                        self.ncmeta.aos.get(path), self.homogeneous_time
                    ) + (f"{metadata.ndim}D",)
                    shape_var = self.group.createVariable(
                        shape_name,
                        SHAPE_DTYPE,
                        dimensions,
                    )
                    doc_indices = ",".join(chr(ord("i") + i) for i in range(3))
                    shape_var.documentation = (
                        f"Shape information for {var_name}.\n"
                        f"{shape_name}[{doc_indices},:] describes the shape of filled "
                        f"data of {var_name}[{doc_indices},...]. Data outside this "
                        "shape is unset (i.e. filled with _Fillvalue)."
                    )

    def store_data(self) -> None:
        """Store data in the netCDF variables"""
        for path, nodes_dict in self.filled_data.items():
            metadata = self.ids.metadata[path]
            var_name = path.replace("/", ".")

            # No data/shapes to store for structures
            if metadata.data_type is IDSDataType.STRUCTURE:
                continue

            shapes = self.shapes.get(path)
            if shapes is not None:
                self.group[f"{var_name}:shape"][()] = shapes

            # No data to store for arrays of structures
            if metadata.data_type is IDSDataType.STRUCT_ARRAY:
                continue

            var = self.group[var_name]
            if var.ndim == metadata.ndim:
                # Not tensorized: directly set value
                node = nodes_dict[()]
                if metadata.data_type is IDSDataType.STR and metadata.ndim == 1:
                    # NetCDF doesn't support setting slices for vlen data types
                    for i in range(len(node)):
                        var[i] = node[i]
                elif shapes is None:
                    # Data is not sparse and we can assign everything
                    var[()] = node.value
                else:
                    # Data is sparse, so we set a slice
                    # var[tuple(map(slice, node.shape))] is equivalent to doing
                    # var[:node.shape[0], :node.shape[1], (etc.)]
                    var[tuple(map(slice, node.shape))] = node.value

            else:
                # Data is tensorized: tensorize in-memory
                var[()] = self.tensorize(path, default_fillvals[metadata.data_type])
