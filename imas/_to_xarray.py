# xarray is an optional dependency, but this module won't be imported when xarray is not
# available
import numpy
import xarray

from imas.ids_toplevel import IDSToplevel
from imas.backends.netcdf.ids_tensorizer import IDSTensorizer
from imas.ids_data_type import IDSDataType

fillvals = {
    IDSDataType.INT: -(2**31) + 1,
    IDSDataType.STR: "",
    IDSDataType.FLT: numpy.nan,
    IDSDataType.CPX: numpy.nan * (1 + 1j),
}


def to_xarray(ids: IDSToplevel, *paths: str) -> xarray.Dataset:
    """See :func:`imas.util.to_xarray`"""
    # We really need an IDS toplevel element
    if not isinstance(ids, IDSToplevel):
        raise TypeError(
            f"to_xarray needs a toplevel IDS element as first argument, but got {ids!r}"
        )

    # Valid path can use / or . as separator, but IDSTensorizer expects /. The following
    # block checks if the paths are valid, and by using "metadata.path_string" we ensure
    # that / are used as separator.
    try:
        paths = [ids.metadata[path].path_string for path in paths]
    except KeyError as exc:
        raise ValueError(str(exc)) from None

    # Converting lazy-loaded IDSs requires users to specify at least one path
    if ids._lazy and not paths:
        raise RuntimeError(
            "This IDS is lazy loaded. Please provide at least one path to convert to"
            " xarray."
        )

    # Use netcdf IDS Tensorizer to tensorize the data and determine metadata
    tensorizer = IDSTensorizer(ids, paths)
    tensorizer.include_coordinate_paths()
    tensorizer.collect_filled_data()
    tensorizer.determine_data_shapes()

    data_vars = {}
    coordinate_names = set()
    for path in tensorizer.filled_data:
        var_name = path.replace("/", ".")
        metadata = ids.metadata[path]
        if metadata.data_type in (IDSDataType.STRUCTURE, IDSDataType.STRUCT_ARRAY):
            continue  # We don't store these in xarray

        dimensions = tensorizer.ncmeta.get_dimensions(path, tensorizer.homogeneous_time)
        data = tensorizer.tensorize(path, fillvals[metadata.data_type])

        attrs = dict(documentation=metadata.documentation)
        if metadata.units:
            attrs["units"] = metadata.units
        coordinates = tensorizer.filter_coordinates(path)
        if coordinates:
            coordinate_names.update(coordinates.split(" "))
            attrs["coordinates"] = coordinates

        data_vars[var_name] = (dimensions, data, attrs)

    # Remove coordinates from data_vars and put in coordinates mapping:
    coordinates = {}
    for coordinate_name in coordinate_names:
        coordinates[coordinate_name] = data_vars.pop(coordinate_name)

    return xarray.Dataset(data_vars, coordinates)
