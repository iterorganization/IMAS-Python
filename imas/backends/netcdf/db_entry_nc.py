"""DBEntry implementation using NetCDF as a backend."""

import logging
from typing import List, Optional, Union

from imas.backends.db_entry_impl import (
    DBEntryImpl,
    GetSampleParameters,
    GetSliceParameters,
)
from imas.backends.netcdf.ids2nc import IDS2NC
from imas.backends.netcdf.nc2ids import NC2IDS
from imas.exception import DataEntryException, InvalidNetCDFEntry
from imas.ids_convert import NBCPathMap, convert_ids
from imas.ids_factory import IDSFactory
from imas.ids_toplevel import IDSToplevel

logger = logging.getLogger(__name__)

try:
    import netCDF4
except ImportError:
    netCDF4 = None
    logger.debug("Could not import netCDF4", exc_info=True)


class NCDBEntryImpl(DBEntryImpl):
    """DBEntry implementation for netCDF storage."""

    def __init__(self, fname: str, mode: str, factory: IDSFactory) -> None:
        if netCDF4 is None:
            raise RuntimeError(
                "The `netCDF4` python module is not available. Please install this "
                "module to read/write IMAS netCDF files with imas-python."
            )

        self._dataset = netCDF4.Dataset(
            fname,
            mode,
            format="NETCDF4",
            auto_complex=True,
        )
        """NetCDF4 dataset."""
        self._factory = factory
        """Factory (DD version) that the user wishes to use."""
        self._ds_factory = factory  # Overwritten if data exists, see _init_dd_version
        """Factory (DD version) that the data is stored in."""

        try:
            self._init_dd_version(fname, mode, factory)
        except Exception:
            self._dataset.close()
            raise

    def _init_dd_version(self, fname: str, mode: str, factory: IDSFactory) -> None:
        """Check or setup data dictionary version."""
        # Check if there is already data in this dataset:
        if self._dataset.dimensions or self._dataset.variables or self._dataset.groups:
            if "data_dictionary_version" not in self._dataset.ncattrs():
                raise InvalidNetCDFEntry(
                    "Invalid netCDF file: `data_dictionary_version` missing"
                )
            dataset_dd_version = self._dataset.data_dictionary_version
            if dataset_dd_version != factory.dd_version:
                self._ds_factory = IDSFactory(dataset_dd_version)

        elif mode not in ["w", "x", "r+", "a"]:
            # Reading an empty file...
            raise InvalidNetCDFEntry(f"Invalid netCDF file: `{fname}` is empty.")
        else:
            # This is an empty netCDF dataset: set global attributes
            self._dataset.Conventions = "IMAS"
            self._dataset.data_dictionary_version = factory.dd_version

    @classmethod
    def from_uri(cls, uri: str, mode: str, factory: IDSFactory) -> "NCDBEntryImpl":
        return cls(uri, mode, factory)

    def close(self, *, erase: bool = False) -> None:
        if erase:
            logger.info(
                "The netCDF backend does not support the `erase` keyword argument "
                "to DBEntry.close(): this argument is ignored."
            )
        self._dataset.close()

    def get(
        self,
        ids_name: str,
        occurrence: int,
        parameters: Union[None, GetSliceParameters, GetSampleParameters],
        destination: IDSToplevel,
        lazy: bool,
        nbc_map: Optional[NBCPathMap],
    ) -> None:
        # Feature compatibility checks
        if parameters is not None:
            if isinstance(parameters, GetSliceParameters):
                func = "get_slice"
            else:
                func = "get_sample"
            raise NotImplementedError(f"`{func}` is not available for netCDF files.")
        if lazy:
            raise NotImplementedError(
                "Lazy loading is not implemented for netCDF files."
            )

        # Check if the IDS/occurrence exists, and obtain the group it is stored in
        try:
            group = self._dataset[f"{ids_name}/{occurrence}"]
        except KeyError:
            raise DataEntryException(
                f"IDS {ids_name!r}, occurrence {occurrence} is not found."
            )

        # Load data into the destination IDS
        if self._ds_factory.dd_version == destination._dd_version:
            NC2IDS(group, destination).run()
        else:
            # FIXME: implement automatic conversion using nbc_map
            #   As a work-around: do an explicit conversion, but automatic conversion
            #   will also be needed to implement lazy loading.
            ids = self._ds_factory.new(ids_name)
            NC2IDS(group, ids).run()
            convert_ids(ids, None, target=destination)

        return destination

    def read_dd_version(self, ids_name: str, occurrence: int) -> str:
        return self._ds_factory.version  # All IDSs must be stored in this DD version

    def put(self, ids: IDSToplevel, occurrence: int, is_slice: bool) -> None:
        if is_slice:
            raise NotImplementedError("`put_slice` is not available for netCDF files.")
        if self._ds_factory.dd_version != ids._dd_version:
            # FIXME: implement automatic conversion?
            raise RuntimeError(
                f"Cannot store an IDS with DD version {ids._dd_version} in a "
                f"netCDF file with DD version {self._ds_factory.version}"
            )

        ids_name = ids.metadata.name
        # netCDF4 limitation: cannot overwrite existing groups
        if ids_name in self._dataset.groups:
            if str(occurrence) in self._dataset[ids_name].groups:
                raise RuntimeError(
                    f"IDS {ids_name}, occurrence {occurrence} already exists. "
                    "Cannot overwrite existing data."
                )

        if hasattr(ids.ids_properties, "version_put"):
            # Ensure the correct DD version:
            ids.ids_properties.version_put.data_dictionary = self._ds_factory.version

        group = self._dataset.createGroup(f"{ids_name}/{occurrence}")
        IDS2NC(ids, group).run()

    def access_layer_version(self) -> str:
        return "N/A"  # We don't use the Access Layer

    def delete_data(self, ids_name: str, occurrence: int) -> None:
        raise NotImplementedError("The netCDF backend does not support deleting IDSs.")

    def list_all_occurrences(self, ids_name: str) -> List[int]:
        occurrence_list = []
        if ids_name in self._dataset.groups:
            for group in self._dataset[ids_name].groups:
                try:
                    occurrence_list.append(int(group))
                except ValueError:
                    logger.warning(
                        "Invalid occurrence %r found for IDS %s", group, ids_name
                    )

        occurrence_list.sort()
        return occurrence_list
