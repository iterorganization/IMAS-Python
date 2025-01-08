from imas.backends.netcdf.db_entry_nc import NCDBEntryImpl
from imas.backends.netcdf.nc2ids import NC2IDS
from imas.db_entry import DBEntry
from imas.exception import InvalidNetCDFEntry


def validate_netcdf_file(filename: str) -> None:
    """Validate if the provided netCDF file adheres to the IMAS conventions."""
    if not filename.endswith(".nc"):
        raise InvalidNetCDFEntry(
            f"Invalid filename `{filename}` provided: "
            "an IMAS netCDF file should end with `.nc`"
        )

    with DBEntry(filename, "r") as entry:
        entry_impl: NCDBEntryImpl = entry._dbe_impl
        dataset = entry_impl._dataset
        factory = entry_impl._ds_factory

        ids_names = factory.ids_names()

        # Check that groups in the dataset correspond to an IDS/occurrence and no
        # additional variables are smuggled inside:
        groups = [dataset] + [dataset[group] for group in dataset.groups]
        for group in groups:
            if group.variables or group.dimensions:
                raise InvalidNetCDFEntry(
                    "NetCDF file should not have variables or dimensions in the "
                    f"{group.name} group."
                )
            if group is dataset:
                continue
            if group.name not in ids_names:
                raise InvalidNetCDFEntry(
                    f"Invalid group name {group.name}: there is no IDS with this name."
                )
            for subgroup in group.groups:
                try:
                    int(subgroup)
                except ValueError:
                    raise InvalidNetCDFEntry(
                        f"Invalid group name {group.name}/{subgroup}: "
                        f"{subgroup} is not a valid occurrence number."
                    )

        for ids_name in ids_names:
            for occurrence in entry.list_all_occurrences(ids_name):
                group = dataset[f"{ids_name}/{occurrence}"]
                try:
                    NC2IDS(group, factory.new(ids_name)).validate_variables()
                except InvalidNetCDFEntry as exc:
                    occ = f":{occurrence}" if occurrence else ""
                    raise InvalidNetCDFEntry(f"Invalid IDS {ids_name}{occ}: {exc}")
