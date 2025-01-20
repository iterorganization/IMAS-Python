import logging
import os
from typing import Iterator, List, Optional, Tuple

import netCDF4

from imas.backends.netcdf import ids2nc
from imas.backends.netcdf.nc_metadata import NCMetadata
from imas.exception import InvalidNetCDFEntry
from imas.ids_base import IDSBase
from imas.ids_data_type import IDSDataType
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS
from imas.ids_metadata import IDSMetadata
from imas.ids_structure import IDSStructure
from imas.ids_toplevel import IDSToplevel

logger = logging.getLogger(__name__)


def variable_error(var, issue, value, expected=None) -> InvalidNetCDFEntry:
    return InvalidNetCDFEntry(
        f"Variable `{var.name}` has incorrect {issue}: `{value}`."
        + (f" Was expecting `{expected}`." if expected is not None else "")
    )


def split_on_aos(metadata: IDSMetadata):
    paths = []
    curpath = metadata.name

    item = metadata
    while item._parent.data_type is not None:
        item = item._parent
        if item.data_type is IDSDataType.STRUCT_ARRAY:
            paths.append(curpath)
            curpath = item.name
        else:
            curpath = f"{item.name}/{curpath}"
    paths.append(curpath)
    return paths[::-1]


IndexedNode = Tuple[Tuple[int, ...], IDSBase]


def tree_iter(structure: IDSStructure, metadata: IDSMetadata) -> Iterator[IndexedNode]:
    paths = split_on_aos(metadata)
    if len(paths) == 1:
        yield (), structure[paths[0]]
    else:
        yield from _tree_iter(structure, paths, ())


def _tree_iter(
    structure: IDSStructure, paths: List[str], curindex: Tuple[int, ...]
) -> Iterator[IndexedNode]:
    aos_path, *paths = paths
    aos = structure[aos_path]

    if len(paths) == 1:
        path = paths[0]
        for i, node in enumerate(aos):
            yield curindex + (i,), node[path]

    else:
        for i, node in enumerate(aos):
            yield from _tree_iter(node, paths, curindex + (i,))


class NC2IDS:
    """Class responsible for reading an IDS from a NetCDF group."""

    def __init__(self, group: netCDF4.Group, ids: IDSToplevel) -> None:
        """Initialize NC2IDS converter.

        Args:
            group: NetCDF group that stores the IDS data.
            ids: Corresponding IDS toplevel to store the data in.
        """
        self.group = group
        """NetCDF Group that the IDS is stored in."""
        self.ids = ids
        """IDS to store the data in."""

        self.ncmeta = NCMetadata(ids.metadata)
        """NetCDF related metadata."""
        self.variables = list(group.variables)
        """List of variable names stored in the netCDF group."""
        # Don't use masked arrays: they're slow and we'll handle most of the unset
        # values through the `:shape` arrays
        self.group.set_auto_mask(False)

        # Validate and get value of ids_properties.homogeneous_time
        self.homogeneous_time = True  # Must be initialized for self._validate_variable
        """True iff the IDS time mode is homogeneous."""

        if "ids_properties.homogeneous_time" not in self.variables:
            raise InvalidNetCDFEntry(
                "Mandatory variable `ids_properties.homogeneous_time` does not exist."
            )
        var = group["ids_properties.homogeneous_time"]
        self._validate_variable(var, ids.ids_properties.homogeneous_time.metadata)
        if var[()] not in [0, 1, 2]:
            raise InvalidNetCDFEntry(
                f"Invalid value for ids_properties.homogeneous_time: {var[()]}. "
                "Was expecting: 0, 1 or 2."
            )
        self.homogeneous_time = var[()] == IDS_TIME_MODE_HOMOGENEOUS

    def run(self) -> None:
        """Load the data from the netCDF group into the IDS."""
        self.variables.sort()
        self.validate_variables()
        for var_name in self.variables:
            if var_name.endswith(":shape"):
                continue
            metadata = self.ids.metadata[var_name]

            if metadata.data_type is IDSDataType.STRUCTURE:
                continue  # This only contains DD metadata we already know

            var = self.group[var_name]
            if metadata.data_type is IDSDataType.STRUCT_ARRAY:
                if "sparse" in var.ncattrs():
                    shapes = self.group[var_name + ":shape"][()]
                    for index, node in tree_iter(self.ids, metadata):
                        node.resize(shapes[index][0])

                else:
                    # FIXME: extract dimension name from nc file?
                    dim = self.ncmeta.get_dimensions(
                        metadata.path_string, self.homogeneous_time
                    )[-1]
                    size = self.group.dimensions[dim].size
                    for _, node in tree_iter(self.ids, metadata):
                        node.resize(size)

                continue

            # FIXME: this may be a gigantic array, not required for sparse data
            var = self.group[var_name]
            data = var[()]

            if "sparse" in var.ncattrs():
                if metadata.ndim:
                    shapes = self.group[var_name + ":shape"][()]
                    for index, node in tree_iter(self.ids, metadata):
                        shape = shapes[index]
                        if shape.all():
                            node.value = data[index + tuple(map(slice, shapes[index]))]
                else:
                    for index, node in tree_iter(self.ids, metadata):
                        value = data[index]
                        if value != getattr(var, "_FillValue", None):
                            node.value = data[index]

            elif metadata.path_string not in self.ncmeta.aos:
                # Shortcut for assigning untensorized data
                self.ids[metadata.path] = data

            else:
                for index, node in tree_iter(self.ids, metadata):
                    node.value = data[index]

    def validate_variables(self) -> None:
        """Validate that all variables in the netCDF Group exist and match the DD."""
        disable_validate = os.environ.get("IMAS_DISABLE_NC_VALIDATE")
        if disable_validate and disable_validate != "0":
            logger.info(
                "NetCDF file validation disabled: "
                "This may lead to errors when reading data!"
            )
            return  # validation checks are disabled

        for var_name in self.variables:
            if var_name.endswith(":shape"):
                # Check that there is a corresponding variable
                data_var = var_name.rpartition(":shape")[0]
                if data_var not in self.variables:
                    raise InvalidNetCDFEntry(
                        f"Invalid netCDF variable: {var_name}. "
                        f"Shape information provided for non-existing {data_var}."
                    )
                # Corresponding variable must be sparse
                if "sparse" not in self.group[data_var].ncattrs():
                    raise InvalidNetCDFEntry(
                        f"Shape information provided for {data_var}, but this variable "
                        "is not sparse."
                    )
                # That's all for :shape arrays here, rest is checked in
                # _validate_variable (which defers to _validate_sparsity)
                continue

            # Check that the DD defines this variable, and validate its metadata
            var = self.group[var_name]
            try:
                metadata = self.ids.metadata[var_name]
            except KeyError:
                raise InvalidNetCDFEntry(
                    f"Invalid variable {var_name}: no such variable exists in the "
                    f"{self.ids.metadata.name} IDS."
                )
            self._validate_variable(var, metadata)

    def _validate_variable(self, var: netCDF4.Variable, metadata: IDSMetadata) -> None:
        """Validate that the variable has correct metadata, raise an exception if not.

        Args:
            var: NetCDF variable
            metadata: IDSMetadata of the corresponding IDS object
        """
        attrs: dict = vars(var).copy()
        attrs.pop("_FillValue", None)
        if metadata.data_type not in [IDSDataType.STRUCTURE, IDSDataType.STRUCT_ARRAY]:
            # Data type
            expected_dtype = ids2nc.dtypes[metadata.data_type]
            if var.dtype != expected_dtype:
                raise variable_error(var, "data type", var.dtype, expected_dtype)

            # Dimensions
            expected_dims = self.ncmeta.get_dimensions(
                metadata.path_string, self.homogeneous_time
            )
            if var.dimensions != expected_dims:
                raise variable_error(var, "dimensions", var.dimensions, expected_dims)

            # Coordinates
            coordinates = str(attrs.pop("coordinates", ""))
            expected_coordinates = self.ncmeta.get_coordinates(
                metadata.path_string, self.homogeneous_time
            )
            if any(coord not in expected_coordinates for coord in coordinates.split()):
                raise variable_error(
                    var, "coordinates", coordinates, " ".join(expected_coordinates)
                )

            # Ancillary variables
            ancvar = attrs.pop("ancillary_variables", None)
            if ancvar:
                allowed_ancvar = [f"{var.name}_error_upper", f"{var.name}_error_lower"]
                if any(var not in allowed_ancvar for var in ancvar.split()):
                    raise variable_error(
                        var, "ancillary_variables", ancvar, " ".join(allowed_ancvar)
                    )

        # Units
        units = attrs.pop("units", None)
        if metadata.units and metadata.units != units:
            raise variable_error(var, "units", units, metadata.units)

        # Sparse
        sparse = attrs.pop("sparse", None)
        if sparse is not None:
            shape_name = f"{var.name}:shape"
            shape_var = self.group[shape_name] if shape_name in self.variables else None
            self._validate_sparsity(var, shape_var, metadata)

        # Documentation
        doc = attrs.pop("documentation", None)
        if metadata.documentation != doc:
            logger.warning("Documentation of variable %s differs from the DD", var.name)

        # Unknown attrs
        if attrs:
            raise variable_error(var, "attributes", list(attrs.keys()))

    def _validate_sparsity(
        self,
        var: netCDF4.Variable,
        shape_var: Optional[netCDF4.Variable],
        metadata: IDSMetadata,
    ) -> None:
        """Validate that the variable has correct sparsity.

        Args:
            var: Variable with a "sparse" attribute
            shape_var: Corresponding shape array (if it exists in the NC group)
            metadata: IDSMetadata of the corresponding IDS object
        """
        if metadata.ndim == 0:
            return  # Sparsity is stored with _Fillvalue, nothing to validate

        # Dimensions
        aos_dimensions = self.ncmeta.get_dimensions(
            self.ncmeta.aos.get(metadata.path_string), self.homogeneous_time
        )
        shape_dimensions = shape_var.dimensions
        if (
            len(shape_dimensions) != len(aos_dimensions) + 1
            or shape_dimensions[:-1] != aos_dimensions
            or self.group.dimensions[shape_dimensions[-1]].size != metadata.ndim
        ):
            expected_dims = aos_dimensions + (f"{metadata.ndim}D",)
            raise variable_error(
                shape_var, "dimensions", shape_dimensions, expected_dims
            )

        # Data type
        if shape_var.dtype.kind not in "ui":  # should be (un)signed integer
            raise variable_error(
                shape_var, "dtype", shape_var.dtype, "any integer type"
            )
