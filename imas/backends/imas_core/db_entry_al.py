"""DBEntry implementation using imas_core as a backend."""

import gc
import getpass
import logging
import os
from collections import deque
from typing import Any, Deque, List, Optional, Union
from urllib.parse import urlparse

from imas.backends.db_entry_impl import GetSampleParameters, GetSliceParameters
from imas.db_entry import DBEntryImpl
from imas.exception import DataEntryException, LowlevelError
from imas.ids_convert import NBCPathMap, dd_version_map_from_factories
from imas.ids_defs import (
    ASCII_BACKEND,
    CHAR_DATA,
    CLOSE_PULSE,
    CREATE_PULSE,
    ERASE_PULSE,
    FORCE_CREATE_PULSE,
    FORCE_OPEN_PULSE,
    HDF5_BACKEND,
    IDS_TIME_MODE_UNKNOWN,
    IDS_TIME_MODES,
    INTEGER_DATA,
    MDSPLUS_BACKEND,
    MEMORY_BACKEND,
    OPEN_PULSE,
    READ_OP,
    UDA_BACKEND,
    UNDEFINED_INTERP,
    UNDEFINED_TIME,
    WRITE_OP,
)
from imas.ids_factory import IDSFactory
from imas.ids_metadata import IDSType
from imas.ids_toplevel import IDSToplevel

from .al_context import ALContext, LazyALContext
from .db_entry_helpers import delete_children, get_children, put_children
from .imas_interface import LLInterfaceError, has_imas, ll_interface
from .mdsplus_model import ensure_data_dir, mdsplus_model_dir
from .uda_support import extract_idsdef, get_dd_version_from_idsdef_xml

_BACKEND_NAME = {
    ASCII_BACKEND: "ascii",
    HDF5_BACKEND: "hdf5",
    MEMORY_BACKEND: "memory",
    MDSPLUS_BACKEND: "mdsplus",
    UDA_BACKEND: "uda",
}
_OPEN_MODES = {
    "r": OPEN_PULSE,
    "a": FORCE_OPEN_PULSE,
    "w": FORCE_CREATE_PULSE,
    "x": CREATE_PULSE,
}

logger = logging.getLogger(__name__)


def require_imas_available():
    if not has_imas:
        raise RuntimeError(
            "The IMAS Core library is not available. Please install 'imas_core', "
            "or load a supported IMAS module if you use an HPC environment."
        )


class ALDBEntryImpl(DBEntryImpl):
    """DBEntry implementation using imas_core as a backend."""

    """Map to the expected open_pulse (AL4) / begin_dataentry_action (AL5) argument."""

    def __init__(self, backend: str, ctx: ALContext, factory: IDSFactory):
        self.backend = backend
        self._db_ctx = ctx
        self._ids_factory = factory
        self._lazy_ctx_cache: Deque[ALContext] = deque()

    @classmethod
    def from_uri(cls, uri: str, mode: str, factory: IDSFactory) -> "ALDBEntryImpl":
        require_imas_available()
        if mode not in _OPEN_MODES:
            modes = list(_OPEN_MODES)
            raise ValueError(f"Unknown mode {mode!r}, was expecting any of {modes}")
        return cls._from_uri(uri, _OPEN_MODES[mode], factory)

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
    ) -> "ALDBEntryImpl":
        # Raise an error if imas is not available
        require_imas_available()

        # Set defaults
        user_name = user_name or getpass.getuser()
        data_version = data_version or factory.dd_version
        options = options if options else ""

        if ll_interface._al_version.major >= 5:
            # We need a URI for AL 5 or later, construct from legacy parameters
            status, uri = ll_interface.build_uri_from_legacy_parameters(
                backend_id, pulse, run, user_name, db_name, data_version, options
            )
            if status != 0:
                raise LowlevelError("build URI from legacy parameters", status)

            return cls._from_uri(uri, mode, factory)

        else:
            # AL4 legacy support:
            backend = _BACKEND_NAME.get(backend_id, "")
            cls._setup_backend(backend, mode, factory, user_name, db_name, run)

            status, ctx = ll_interface.begin_pulse_action(
                backend_id, pulse, run, user_name, db_name, data_version
            )
            if status != 0:
                raise LowlevelError("begin pulse action", status)

            status = ll_interface.open_pulse(ctx, mode, options)
            if status != 0:
                raise LowlevelError("opening/creating data entry", status)

            return cls(backend, ALContext(ctx), factory)

    @classmethod
    def _from_uri(cls, uri: str, mode: int, factory: IDSFactory) -> "ALDBEntryImpl":
        """Helper method to actually open/create the dataentry."""
        backend = urlparse(uri).path.lower().lstrip("/")
        cls._setup_backend(backend, mode, factory)

        status, ctx = ll_interface.begin_dataentry_action(uri, mode)
        if status != 0:
            raise LowlevelError("opening/creating data entry", status)

        return cls(backend, ALContext(ctx), factory)

    @classmethod
    def _setup_backend(
        cls,
        backend: str,
        mode: int,
        factory: IDSFactory,
        user_name: str = "",
        db_name="",
        run=1,
    ) -> None:
        """Custom logic for preparing some backends.

        Note: user_name, db_name and run are only used for AL 4.x, they can be
        omitted when using AL 5 or later.
        """
        if backend == "mdsplus":
            # MDSplus models:
            if mode != OPEN_PULSE:
                # Building the MDS+ models is required when creating a new Data Entry
                ids_path = mdsplus_model_dir(factory)
                if ids_path:
                    os.environ["ids_path"] = ids_path

            if ll_interface._al_version.major == 4:
                # Ensure the data directory exists
                # Note: MDSPLUS model directory only uses the major version component of
                # IMAS_VERSION, so we'll take the first character of IMAS_VERSION:
                version = factory.version[0]
                ensure_data_dir(user_name, db_name, version, run)

        elif backend == "hdf5":
            pass  # nothing to set up

        elif backend == "memory":
            pass  # nothing to set up

        elif backend == "ascii":
            pass  # nothing to set up

        elif backend == "uda":
            # Set IDSDEF_PATH to point the UDA backend to the selected DD version
            idsdef_path = None

            if factory._xml_path is not None:
                # Factory was constructed with an explicit XML path, point UDA to that:
                idsdef_path = factory._xml_path

            elif "IMAS_PREFIX" in os.environ:
                # Check if UDA can use the IDSDef.xml stored in $IMAS_PREFIX/include/
                idsdef_path = os.environ["IMAS_PREFIX"] + "/include/IDSDef.xml"
                if get_dd_version_from_idsdef_xml(idsdef_path) != factory.version:
                    idsdef_path = None

            if idsdef_path is None:
                # Extract XML from the DD zip and point UDA to it
                idsdef_path = extract_idsdef(factory.version)

            os.environ["IDSDEF_PATH"] = idsdef_path
            logger.warning(
                "The UDA backend is not tested with "
                "imas-python and may not work properly. "
                "Please raise any issues you find."
            )

        elif backend == "flexbuffers":
            pass  # nothing to set up

        else:
            logger.warning("Backend %s is unknown to imas-python", backend)

    def close(self, *, erase: bool = False) -> None:
        if self._db_ctx is None:
            return

        self._clear_lazy_ctx_cache()

        mode = ERASE_PULSE if erase else CLOSE_PULSE
        status = ll_interface.close_pulse(self._db_ctx.ctx, mode)
        if status != 0:
            raise LowlevelError("close data entry", status)

        ll_interface.end_action(self._db_ctx.ctx)
        self._db_ctx = None

    def _clear_lazy_ctx_cache(self) -> None:
        """Close any cached lazy contexts"""
        while self._lazy_ctx_cache:
            self._lazy_ctx_cache.pop().close()

    def get(
        self,
        ids_name: str,
        occurrence: int,
        parameters: Union[None, GetSliceParameters, GetSampleParameters],
        destination: IDSToplevel,
        lazy: bool,
        nbc_map: Optional[NBCPathMap],
    ) -> None:
        if self._db_ctx is None:
            raise RuntimeError("Database entry is not open.")
        if lazy and self.backend == "ascii":
            raise RuntimeError("Lazy loading is not supported by the ASCII backend.")

        # Mixing contexts can be problematic, ensure all lazy contexts are closed:
        self._clear_lazy_ctx_cache()

        ll_path = ids_name
        if occurrence != 0:
            ll_path += f"/{occurrence}"

        with self._db_ctx.global_action(ll_path, READ_OP) as read_ctx:
            time_mode_path = "ids_properties/homogeneous_time"
            time_mode = read_ctx.read_data(time_mode_path, "", INTEGER_DATA, 0)
            # This is already checked by read_dd_version, but ensure:
            assert time_mode in IDS_TIME_MODES

        if lazy:
            context = LazyALContext(dbentry=self, nbc_map=nbc_map, time_mode=time_mode)
        else:
            context = self._db_ctx
        # Now fill the IDSToplevel
        if parameters is None or destination.metadata.type is IDSType.CONSTANT:
            # called from get(), or when the IDS is constant (see IMAS-3330)
            manager = context.global_action(ll_path, READ_OP)
        elif isinstance(parameters, GetSliceParameters):
            manager = context.slice_action(
                ll_path,
                READ_OP,
                parameters.time_requested,
                parameters.interpolation_method,
            )
        elif isinstance(parameters, GetSampleParameters):
            manager = context.timerange_action(
                ll_path,
                READ_OP,
                parameters.tmin,
                parameters.tmax,
                parameters.dtime,
                parameters.interpolation_method,
            )
        else:
            raise TypeError(f"Incorrect type for parameters: {type(parameters)}.")

        with manager as read_ctx:
            if lazy:
                destination._set_lazy_context(read_ctx)
            else:
                # Get may create LOTS of new objects. Temporarily disable Python's
                # garbage collector to speed up the get:
                gc_enabled = gc.isenabled()
                gc.disable()
                get_children(destination, read_ctx, time_mode, nbc_map)
                if gc_enabled:
                    gc.enable()

        return destination

    def read_dd_version(self, ids_name: str, occurrence: int) -> str:
        if self._db_ctx is None:
            raise RuntimeError("Database entry is not open.")
        # Mixing contexts can be problematic, ensure all lazy contexts are closed:
        self._clear_lazy_ctx_cache()

        ll_path = ids_name
        if occurrence != 0:
            ll_path += f"/{occurrence}"

        with self._db_ctx.global_action(ll_path, READ_OP) as read_ctx:
            time_mode_path = "ids_properties/homogeneous_time"
            time_mode = read_ctx.read_data(time_mode_path, "", INTEGER_DATA, 0)
            dd_version_path = "ids_properties/version_put/data_dictionary"
            dd_version = read_ctx.read_data(dd_version_path, "", CHAR_DATA, 1)

        if time_mode not in IDS_TIME_MODES:
            raise DataEntryException(
                f"IDS {ids_name!r}, occurrence {occurrence} is empty."
            )
        return dd_version

    def put(self, ids: IDSToplevel, occurrence: int, is_slice: bool) -> None:
        if self._db_ctx is None:
            raise RuntimeError("Database entry is not open.")

        # Mixing contexts can be problematic, ensure all lazy contexts are closed:
        self._clear_lazy_ctx_cache()

        ids_name = ids.metadata.name
        # Create a version conversion map, if needed
        nbc_map = None
        if ids._version != self._ids_factory._version:
            ddmap, source_is_older = dd_version_map_from_factories(
                ids_name, ids._parent, self._ids_factory
            )
            nbc_map = ddmap.old_to_new if source_is_older else ddmap.new_to_old

        ll_path = ids_name
        if occurrence != 0:
            ll_path += f"/{occurrence}"

        time_mode = ids.ids_properties.homogeneous_time
        if is_slice:
            with self._db_ctx.global_action(ll_path, READ_OP) as read_ctx:
                db_time_mode = read_ctx.read_data(
                    "ids_properties/homogeneous_time", "", INTEGER_DATA, 0
                )
            if db_time_mode == IDS_TIME_MODE_UNKNOWN:
                # No data yet on disk, so just put everything
                is_slice = False
            elif db_time_mode != time_mode:
                raise DataEntryException(
                    f"Cannot change homogeneous_time from {db_time_mode} to {time_mode}"
                )

        if not is_slice:
            # put() must first delete any existing data
            with self._db_ctx.global_action(ll_path, WRITE_OP) as write_ctx:
                # New IDS to ensure all fields in "our" DD version are deleted
                # If ids is in another version, we might not erase all fields
                delete_children(self._ids_factory.new(ids_name).metadata, write_ctx)

        if is_slice:
            manager = self._db_ctx.slice_action(
                ll_path, WRITE_OP, UNDEFINED_TIME, UNDEFINED_INTERP
            )
        else:
            manager = self._db_ctx.global_action(ll_path, WRITE_OP)
        verify_maxoccur = self.backend == "mdsplus"
        with manager as write_ctx:
            put_children(ids, write_ctx, time_mode, is_slice, nbc_map, verify_maxoccur)

    def access_layer_version(self) -> str:
        return ll_interface._al_version_str

    def delete_data(self, ids_name: str, occurrence: int) -> None:
        if self._db_ctx is None:
            raise RuntimeError("Database entry is not open.")
        # Mixing contexts can be problematic, ensure all lazy contexts are closed:
        self._clear_lazy_ctx_cache()

        ll_path = ids_name
        if occurrence != 0:
            ll_path += f"/{occurrence}"
        ids = self._ids_factory.new(ids_name)
        with self._db_ctx.global_action(ll_path, WRITE_OP) as write_ctx:
            delete_children(ids.metadata, write_ctx, "")

    def list_all_occurrences(self, ids_name: str) -> List[int]:
        try:
            occurrence_list = self._db_ctx.list_all_occurrences(ids_name)
        except LLInterfaceError:
            # al_get_occurrences is not available in the lowlevel
            raise RuntimeError(
                "list_all_occurrences is not available. "
                "Access Layer 5.1 or newer is required."
            ) from None
        return occurrence_list
