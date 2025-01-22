# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, Union

import numpy

from imas.ids_convert import NBCPathMap
from imas.ids_factory import IDSFactory
from imas.ids_toplevel import IDSToplevel


@dataclass
class GetSliceParameters:
    """Helper class to store parameters to get_slice."""

    time_requested: float
    """See :param:`imas.db_entry.DBEntry.get_slice.time_requested`."""
    interpolation_method: int
    """See :param:`imas.db_entry.DBEntry.get_slice.interpolation_method`."""


@dataclass
class GetSampleParameters:
    """Helper class to store parameters to get_sample."""

    tmin: float
    """See :param:`imas.db_entry.DBEntry.get_sample.tmin`."""
    tmax: float
    """See :param:`imas.db_entry.DBEntry.get_sample.tmax`."""
    dtime: Optional[numpy.ndarray]
    """See :param:`imas.db_entry.DBEntry.get_sample.dtime`."""
    interpolation_method: Optional[int]
    """See :param:`imas.db_entry.DBEntry.get_sample.interpolation_method`."""


class DBEntryImpl(ABC):
    """Interface for DBEntry implementations."""

    @classmethod
    @abstractmethod
    def from_uri(cls, uri: str, mode: str, factory: IDSFactory) -> "DBEntryImpl":
        """Open a datasource by URI."""

    @classmethod
    def from_pulse_run(
        cls,
        backend_id: int,
        db_name: str,
        pulse: int,
        run: int,
        user_name: Optional[str],
        data_version: Optional[str],
        mode: int,
        options: Any,
        factory: IDSFactory,
    ) -> "DBEntryImpl":
        """Open a datasource with pulse, run and other legacy arguments."""
        raise NotImplementedError()  # Only the `imas_core` backend implements this.

    @abstractmethod
    def close(self, *, erase: bool = False) -> None:
        """Close the data source.

        Keyword Args:
            erase: The Access Layer allowed a parameter to erase data files when
                closing. This parameter may be ignored when implementing a backend.
        """

    @abstractmethod
    def get(
        self,
        ids_name: str,
        occurrence: int,
        parameters: Union[None, GetSliceParameters, GetSampleParameters],
        destination: IDSToplevel,
        lazy: bool,
        nbc_map: Optional[NBCPathMap],
    ) -> None:
        """Implement DBEntry.get/get_slice/get_sample. Load data from the data source.

        Args:
            ids_name: Name of the IDS to load.
            occurrence: Which occurence of the IDS to load.
            parameters: Additional parameters for a get_slice/get_sample call.
            destination: IDS object to store data in.
            lazy: Use lazy loading.
            nbc_map: NBCPathMap to use for implicit conversion. When None, no implicit
                conversion needs to be done.
        """

    @abstractmethod
    def read_dd_version(self, ids_name: str, occurrence: int) -> str:
        """Read data dictionary version that the requested IDS was stored with.

        This method should raise a DataEntryException if the specified ids/occurrence is
        not filled.
        """

    @abstractmethod
    def put(self, ids: IDSToplevel, occurrence: int, is_slice: bool) -> None:
        """Implement DBEntry.put()/put_slice(): store data.

        Args:
            ids: IDS to store in the data source.
            occurrence: Which occurrence of the IDS to store to.
            is_slice: True: put_slice(), False: put()
        """

    @abstractmethod
    def access_layer_version(self) -> str:
        """Get the access layer version used to store data."""

    @abstractmethod
    def delete_data(self, ids_name: str, occurrence: int) -> None:
        """Implement DBEntry.delete_data()"""

    @abstractmethod
    def list_all_occurrences(self, ids_name: str) -> List[int]:
        """Implement DBEntry.list_all_occurrences()"""
