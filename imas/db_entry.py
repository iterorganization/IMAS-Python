# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Logic for interacting with IMAS Data Entries.
"""

import logging
import os
from typing import Any, List, Optional, Tuple, Type, Union, overload

import numpy

import imas
from imas.backends.db_entry_impl import (
    DBEntryImpl,
    GetSampleParameters,
    GetSliceParameters,
)
from imas.dd_zip import dd_xml_versions
from imas.exception import IDSNameError, UnknownDDVersion, ValidationError
from imas.ids_base import IDSBase
from imas.ids_convert import dd_version_map_from_factories
from imas.ids_defs import (
    CREATE_PULSE,
    FORCE_CREATE_PULSE,
    FORCE_OPEN_PULSE,
    IDS_TIME_MODE_INDEPENDENT,
    IDS_TIME_MODES,
    OPEN_PULSE,
)
from imas.ids_factory import IDSFactory
from imas.ids_metadata import IDSType
from imas.ids_toplevel import IDSToplevel

logger = logging.getLogger(__name__)


def _get_uri_mode(uri, mode) -> Tuple[str, str]:
    """Helper method to parse arguments of DBEntry.__init__."""
    return uri, mode


def _get_legacy_params(
    backend_id, db_name, pulse, run, user_name=None, data_version=None
) -> Tuple[int, str, int, int, Optional[str], Optional[str]]:
    """Helper method to parse arguments of DBEntry.__init__."""
    return backend_id, db_name, pulse, run, user_name, data_version


class DBEntry:
    """Represents an IMAS database entry, which is a collection of stored IDSs.

    A ``DBEntry`` can be used as a :external:ref:`context manager <context-managers>`:

    .. code-block:: python

        import imas

        # old constructor:
        with imas.DBEntry(imas.ids_defs.HDF5_BACKEND, "test", 1, 12) as dbentry:
            # dbentry is now opened and can be used for reading data:
            ids = dbentry.get(...)
        # The dbentry is now closed

        # new constructor also allows creating the Data Entry with the mode
        # argument
        with imas.DBEntry("imas:hdf5?path=testdb", "w") as dbentry:
            # dbentry is now created and can be used for writing data:
            dbentry.put(ids)
        # The dbentry is now closed
    """

    @overload
    def __init__(
        self,
        uri: str,
        mode: str,
        *,
        dd_version: Optional[str] = None,
        xml_path: Optional[str] = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        backend_id: int,
        db_name: str,
        pulse: int,
        run: int,
        user_name: Optional[str] = None,
        data_version: Optional[str] = None,
        *,
        shot: Optional[int] = None,
        dd_version: Optional[str] = None,
        xml_path: Optional[str] = None,
    ) -> None: ...

    def __init__(
        self,
        *args,
        dd_version: Optional[str] = None,
        xml_path: Optional[str] = None,
        **kwargs,
    ):
        """Open or create a Data Entry based on the provided URI and mode, or prepare a
        DBEntry using `legacy` parameters.

        Note:
            When using `legacy` parameters (:param:`backend_id`, :param:`db_name`,
            :param:`pulse`, :param:`run`), the DBEntry is not opened.
            You have to call :meth:`open` or :meth:`create` after creating the DBEntry
            object before you can use it for reading or writing data.

        Args:
            uri: URI to the data entry, see explanation above.
            mode: Mode to open the Data Entry in:

              - ``"r"``: Open an existing data entry. Raises an error when the data
                entry does not exist.

                .. note:: The opened data entry is not read-only, it can be written to.
              - ``"a"``: Open an existing data entry, create the data entry if it does
                not exist.
              - ``"w"``: Create a data entry, overwriting any existing.

                .. caution:: This will irreversibly delete any existing data.
              - ``"x"``: Create a data entry. Raises an error when a data entry already
                exists.

            backend_id: ID of the backend to use. See :ref:`Backend identifiers`.
            db_name: Database name, e.g. "ITER".
            pulse: Pulse number of the database entry.
            run: Run number of the database entry.
            user_name: User name of the database, retrieved from environment when not
                supplied.
            data_version: Major version of the DD used by the the access layer.

        Keyword Args:
            shot: Legacy alternative for :param:`pulse`.
            dd_version: Use a specific Data Dictionary version instead of the default
                one. See :ref:`multi-dd training`.
            xml_path: Use a specific Data Dictionary build by pointing to the
                IDSDef.xml. See :ref:`Using custom builds of the Data Dictionary`.
        """
        try:
            # Try to map *args and **kwargs to (uri, mode)
            uri, mode = _get_uri_mode(*args, **kwargs)
            legacy = False

        except TypeError as exc1:
            # map legacy `shot` to `pulse`
            if "shot" in kwargs:
                if "pulse" in kwargs:
                    raise ValueError("Cannot provide a value for both shot and pulse")
                kwargs["pulse"] = kwargs.pop("shot")
            # Try to map *args and **kwargs to legacy call pattern
            try:
                legacy_params = _get_legacy_params(*args, **kwargs)
                legacy = True
            except TypeError as exc2:
                raise TypeError(
                    f"Incorrect arguments to {__class__.__name__}.__init__(): "
                    f"{exc1.args[0]}, {exc2.args[0]}"
                ) from None

        # Actual intializiation
        self._dbe_impl: Optional[DBEntryImpl] = None
        self._dd_version = dd_version
        self._xml_path = xml_path
        self._ids_factory = IDSFactory(dd_version, xml_path)

        if legacy:
            # Unpack legacy params
            (
                self.backend_id,
                self.db_name,
                self.pulse,
                self.run,
                self.user_name,
                self.data_version,
            ) = legacy_params
            self.uri = None
            self.mode = None
        else:
            self.uri = str(uri)
            self.mode = mode
            cls = self._select_implementation(self.uri)
            self._dbe_impl = cls.from_uri(self.uri, mode, self._ids_factory)

    @staticmethod
    def _select_implementation(uri: Optional[str]) -> Type[DBEntryImpl]:
        """Select which DBEntry implementation to use based on the URI."""
        if uri and uri.endswith(".nc") and not uri.startswith("imas:"):
            from imas.backends.netcdf.db_entry_nc import NCDBEntryImpl as impl
        else:
            from imas.backends.imas_core.db_entry_al import ALDBEntryImpl as impl
        return impl

    def __enter__(self):
        # Context manager protocol
        if self._dbe_impl is None:
            # Open if the DBEntry was not already opened or created
            self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Context manager protocol
        self.close()

    @property
    def factory(self) -> IDSFactory:
        """Get the IDS factory used by this DB entry."""
        return self._ids_factory

    @property
    def dd_version(self) -> str:
        """Get the DD version used by this DB entry"""
        return self._ids_factory.version

    def close(self, *, erase=False):
        """Close this Database Entry.

        Keyword Args:
            erase: Remove the pulse file from the database. Note: this parameter may be
                ignored by the backend. It is best to not use it.
        """
        if self._dbe_impl is None:
            return
        self._dbe_impl.close(erase=erase)
        self._dbe_impl = None

    def create(self, *, options=None, force=True) -> None:
        """Create a new database entry.

        This method may not be called when using the URI constructor of DBEntry.

        Caution:
            This method erases the previous entry if it existed!

        Keyword Args:
            options: Backend specific options.
            force: Whether to force create the database entry.

        Example:
            .. code-block:: python

                import imas
                from imas.ids_defs import HDF5_BACKEND

                imas_entry = imas.DBEntry(HDF5_BACKEND, "test", 1, 1234)
                imas_entry.create()
        """
        self._open_pulse(FORCE_CREATE_PULSE if force else CREATE_PULSE, options)

    def open(self, mode=OPEN_PULSE, *, options=None, force=False) -> None:
        """Open an existing database entry.

        This method may not be called when using the URI constructor of DBEntry.

        Keyword Args:
            options: Backend specific options.
            force: Whether to force open the database entry.

        Example:
            .. code-block:: python

                import imas
                from imas.ids_defs import HDF5_BACKEND

                imas_entry = imas.DBEntry(HDF5_BACKEND, "test", 1, 1234)
                imas_entry.open()
        """
        if force:
            mode = FORCE_OPEN_PULSE
            logger.warning(
                "DBEntry.open(force=True) is deprecated, "
                "use DBEntry.open(FORCE_OPEN_PULSE) instead"
            )
        self._open_pulse(mode, options)

    def _open_pulse(self, mode: int, options: Any) -> None:
        """Internal method implementing open()/create()."""
        if self._dbe_impl is not None:
            raise RuntimeError("This DBEntry is already open")
        if self.uri is not None:
            raise RuntimeError(
                "This DBEntry was opened using an URI: "
                "DBEntry.open/create is not available."
            )

        cls = self._select_implementation(self.uri)
        self._dbe_impl = cls.from_pulse_run(
            self.backend_id,
            self.db_name,
            self.pulse,
            self.run,
            self.user_name,
            self.data_version,
            mode,
            options,
            self._ids_factory,
        )

    def get(
        self,
        ids_name: str,
        occurrence: int = 0,
        *,
        lazy: bool = False,
        autoconvert: bool = True,
        ignore_unknown_dd_version: bool = False,
        destination: Optional[IDSToplevel] = None,
    ) -> IDSToplevel:
        """Read the contents of an IDS into memory.

        This method fetches an IDS in its entirety, with all time slices it may contain.
        See :meth:`get_slice` for reading a specific time slice.

        Args:
            ids_name: Name of the IDS to read from the backend.
            occurrence: Which occurrence of the IDS to read.

        Keyword Args:
            lazy: When set to ``True``, values in this IDS will be retrieved only when
                needed (instead of getting the full IDS immediately). See :ref:`Lazy
                loading` for more details.

                .. note:: Lazy loading is not supported by the ASCII backend.
            autoconvert: Automatically convert IDSs.

                If enabled (default), a call to ``get()`` or ``get_slice()`` will return
                an IDS from the Data Dictionary version attached to this Data Entry.
                Data is automatically converted between the on-disk version and the
                in-memory version.

                When set to ``False``, the IDS will be returned in the DD version it was
                stored in.
            ignore_unknown_dd_version: When an IDS is stored with an unknown DD version,
                do not attempt automatic conversion and fetch the data in the Data
                Dictionary version attached to this Data Entry.
            destination: Populate this IDSToplevel instead of creating an empty one.

        Returns:
            The loaded IDS.

        Example:
            .. code-block:: python

                import imas

                imas_entry = imas.DBEntry(imas.ids_defs.MDSPLUS_BACKEND, "ITER", 131024, 41, "public")
                imas_entry.open()
                core_profiles = imas_entry.get("core_profiles")
        """  # noqa
        return self._get(
            ids_name,
            occurrence,
            None,
            destination,
            lazy,
            autoconvert,
            ignore_unknown_dd_version,
        )

    def get_slice(
        self,
        ids_name: str,
        time_requested: float,
        interpolation_method: int,
        occurrence: int = 0,
        *,
        lazy: bool = False,
        autoconvert: bool = True,
        ignore_unknown_dd_version: bool = False,
        destination: Optional[IDSToplevel] = None,
    ) -> IDSToplevel:
        """Read a single time slice from an IDS in this Database Entry.

        This method returns an IDS object with all constant/static data filled. The
        dynamic data is interpolated on the requested time slice. This means that the
        size of the time dimension in the returned data is 1.

        Args:
            ids_name: Name of the IDS to read from the backend.
            time_requested: Requested time slice
            interpolation_method: Interpolation method to use. Available options:

                - :const:`~imas.ids_defs.CLOSEST_INTERP`
                - :const:`~imas.ids_defs.PREVIOUS_INTERP`
                - :const:`~imas.ids_defs.LINEAR_INTERP`

            occurrence: Which occurrence of the IDS to read.

        Keyword Args:
            lazy: When set to ``True``, values in this IDS will be retrieved only when
                needed (instead of getting the full IDS immediately). See :ref:`Lazy
                loading` for more details.
            autoconvert: Automatically convert IDSs.

                If enabled (default), a call to ``get()`` or ``get_slice()`` will return
                an IDS from the Data Dictionary version attached to this Data Entry.
                Data is automatically converted between the on-disk version and the
                in-memory version.

                When set to ``False``, the IDS will be returned in the DD version it was
                stored in.
            ignore_unknown_dd_version: When an IDS is stored with an unknown DD version,
                do not attempt automatic conversion and fetch the data in the Data
                Dictionary version attached to this Data Entry.
            destination: Populate this IDSToplevel instead of creating an empty one.

        Returns:
            The loaded IDS.

        Example:
            .. code-block:: python

                import imas

                imas_entry = imas.DBEntry(imas.ids_defs.MDSPLUS_BACKEND, "ITER", 131024, 41, "public")
                imas_entry.open()
                core_profiles = imas_entry.get_slice("core_profiles", 370, imas.ids_defs.PREVIOUS_INTERP)
        """  # noqa
        return self._get(
            ids_name,
            occurrence,
            GetSliceParameters(time_requested, interpolation_method),
            destination,
            lazy,
            autoconvert,
            ignore_unknown_dd_version,
        )

    def get_sample(
        self,
        ids_name: str,
        tmin: float,
        tmax: float,
        dtime: Optional[Union[float, numpy.ndarray]] = None,
        interpolation_method: Optional[int] = None,
        occurrence: int = 0,
        *,
        lazy: bool = False,
        autoconvert: bool = True,
        ignore_unknown_dd_version: bool = False,
        destination: Optional[IDSToplevel] = None,
    ) -> IDSToplevel:
        """Read a range of time slices from an IDS in this Database Entry.

        This method has three different modes, depending on the provided arguments:

        1.  No interpolation. This method is selected when :param:`dtime` and
            :param:`interpolation_method` are not provided.

            This mode returns an IDS object with all constant/static data filled. The
            dynamic data is retrieved for the provided time range [tmin, tmax].

        2.  Interpolate dynamic data on a uniform time base. This method is selected
            when :param:`dtime` and :param:`interpolation_method` are provided.
            :param:`dtime` must be a number or a numpy array of size 1.

            This mode will generate an IDS with a homogeneous time vector ``[tmin, tmin
            + dtime, tmin + 2*dtime, ...`` up to ``tmax``. The chosen interpolation
            method will have no effect on the time vector, but may have an impact on the
            other dynamic values. The returned IDS always has
            ``ids_properties.homogeneous_time = 1``.

        3.  Interpolate dynamic data on an explicit time base. This method is selected
            when :param:`dtime` and :param:`interpolation_method` are provided.
            :param:`dtime` must be a numpy array of size larger than 1.

            This mode will generate an IDS with a homogeneous time vector equal to
            :param:`dtime`. :param:`tmin` and :param:`tmax` are ignored in this mode.
            The chosen interpolation method will have no effect on the time vector, but
            may have an impact on the other dynamic values. The returned IDS always has
            ``ids_properties.homogeneous_time = 1``.

        Args:
            ids_name: Name of the IDS to read from the backend
            tmin: Lower bound of the requested time range
            tmax: Upper bound of the requested time range, must be larger than or
                equal to :param:`tmin`
            dtime: Interval to use when interpolating, must be positive, or numpy array
                containing an explicit time base to interpolate.
            interpolation_method: Interpolation method to use. Available options:

                - :const:`~imas.ids_defs.CLOSEST_INTERP`
                - :const:`~imas.ids_defs.PREVIOUS_INTERP`
                - :const:`~imas.ids_defs.LINEAR_INTERP`

            occurrence: Which occurrence of the IDS to read.

        Keyword Args:
            lazy: When set to ``True``, values in this IDS will be retrieved only when
                needed (instead of getting the full IDS immediately). See :ref:`Lazy
                loading` for more details.
            autoconvert: Automatically convert IDSs.

                If enabled (default), a call to ``get_sample()`` will return
                an IDS from the Data Dictionary version attached to this Data Entry.
                Data is automatically converted between the on-disk version and the
                in-memory version.

                When set to ``False``, the IDS will be returned in the DD version it was
                stored in.
            ignore_unknown_dd_version: When an IDS is stored with an unknown DD version,
                do not attempt automatic conversion and fetch the data in the Data
                Dictionary version attached to this Data Entry.
            destination: Populate this IDSToplevel instead of creating an empty one.

        Returns:
            The loaded IDS.

        Example:
            .. code-block:: python

                import imas
                import numpy
                from imas import ids_defs

                imas_entry = imas.DBEntry(
                    "imas:mdsplus?user=public;pulse=131024;run=41;database=ITER", "r")

                # All time slices between t=200 and t=370
                core_profiles = imas_entry.get_sample("core_profiles", 200, 370)

                # Closest points to [0, 100, 200, ..., 1000]
                core_profiles_interp = imas_entry.get_sample(
                    "core_profiles", 0, 1000, 100, ids_defs.CLOSEST_INTERP)

                # Linear interpolation for [10, 11, 12, 14, 16, 20, 30, 40, 50]
                times = numpy.array([10, 11, 12, 14, 16, 20, 30, 40, 50])
                core_profiles_interp = imas_entry.get_sample(
                    "core_profiles", 0, 0, times, ids_defs.LINEAR_INTERP)
        """
        if dtime is not None:
            dtime = numpy.atleast_1d(dtime)  # Convert floats and 0D arrays to 1D array
        return self._get(
            ids_name,
            occurrence,
            GetSampleParameters(tmin, tmax, dtime, interpolation_method),
            destination,
            lazy,
            autoconvert,
            ignore_unknown_dd_version,
        )

    def _get(
        self,
        ids_name: str,
        occurrence: int,
        parameters: Union[None, GetSliceParameters, GetSampleParameters],
        destination: Optional[IDSToplevel],
        lazy: bool,
        autoconvert: bool,
        ignore_unknown_dd_version: bool,
    ) -> IDSToplevel:
        """Actual implementation of get() and get_slice()"""
        if self._dbe_impl is None:
            raise RuntimeError("Database entry is not open.")
        if lazy and destination:
            raise ValueError("Cannot supply a destination IDS when lazy loading.")
        if not self._ids_factory.exists(ids_name):
            raise IDSNameError(ids_name, self._ids_factory)

        # Note: this will raise an exception when the ids/occurrence is not filled:
        dd_version = self._dbe_impl.read_dd_version(ids_name, occurrence)

        # DD version sanity checks:
        if not dd_version:
            # No DD version stored in the IDS, load as if it was stored with
            # self.dd_version
            logger.warning(
                "Loaded IDS (%s, occurrence %s) does not specify a data dictionary "
                "version. Some data may not be loaded.",
                ids_name,
                occurrence,
            )
        elif dd_version != self.dd_version and dd_version not in dd_xml_versions():
            # We don't know the DD version that this IDS was written with
            if ignore_unknown_dd_version:
                # User chooses to ignore this problem, load as if it was stored with
                # self.dd_version
                logger.info("Ignoring unknown data dictionary version %s", dd_version)
                dd_version = None
            else:
                note = (
                    "\nYou may set the get/get_slice parameter "
                    "ignore_unknown_dd_version=True to ignore this and get an IDS in "
                    f"the default DD version ({self.dd_version})"
                )
                raise UnknownDDVersion(dd_version, dd_xml_versions(), note)

        # Version conversion:
        if not destination:
            # Construct IDS object that the backend can store data in
            if autoconvert or not dd_version:
                # Store results in our DD version
                destination = self._ids_factory.new(ids_name, _lazy=lazy)
            else:
                # Store results in the on-disk version
                destination = IDSFactory(dd_version).new(ids_name, _lazy=lazy)

        nbc_map = None
        if dd_version and dd_version != destination._dd_version:
            if dd_version.split(".")[0] != destination._dd_version.split(".")[0]:
                logger.warning(
                    "On-disk data is stored in DD %s which has a different major "
                    "version than the requested DD version (%s). imas-python will "
                    "convert the data automatically, but this does not cover all"
                    "changes. "
                    "See %s/multi-dd.html#conversion-of-idss-between-dd-versions",
                    dd_version,
                    destination._dd_version,
                    imas.PUBLISHED_DOCUMENTATION_ROOT,
                )
            ddmap, source_is_older = dd_version_map_from_factories(
                ids_name, IDSFactory(version=dd_version), self._ids_factory
            )
            nbc_map = ddmap.new_to_old if source_is_older else ddmap.old_to_new

        # Pass on to the DBEntry implementation:
        return self._dbe_impl.get(
            ids_name,
            occurrence,
            parameters,
            destination,
            lazy,
            nbc_map,
        )

    def put(self, ids: IDSToplevel, occurrence: int = 0) -> None:
        """Write the contents of an IDS into this Database Entry.

        The IDS is written entirely, with all time slices it may contain.

        Caution:
            The put method deletes any previously existing data within the target IDS
            occurrence in the Database Entry.

        Args:
            ids: IDS object to put.
            occurrence: Which occurrence of the IDS to write to.

        Example:
            .. code-block:: python

                ids = imas.IDSFactory().pf_active()
                ...  # fill the pf_active IDS here
                imas_entry.put(ids)
        """
        self._put(ids, occurrence, False)

    def put_slice(self, ids: IDSToplevel, occurrence: int = 0) -> None:
        """Append a time slice of the provided IDS to the Database Entry.

        Time slices must be appended in strictly increasing time order, since the Access
        Layer is not reordering time arrays. Doing otherwise will result in
        non-monotonic time arrays, which will create confusion and make subsequent
        :meth:`get_slice` commands to fail.

        Although being put progressively time slice by time slice, the final IDS must be
        compliant with the data dictionary. A typical error when constructing IDS
        variables time slice by time slice is to change the size of the IDS fields
        during the time loop, which is not allowed but for the children of an array of
        structure which has time as its coordinate.

        The :meth:`put_slice` command is appending data, so does not modify previously
        existing data within the target IDS occurrence in the Data Entry.

        It is possible possible to append several time slices to a node of the IDS in
        one :meth:`put_slice` call, however the user must ensure that the size of the
        time dimension of the node remains consistent with the size of its timebase.

        Args:
            ids: IDS object to put.
            occurrence: Which occurrence of the IDS to write to.

        Example:
            A frequent use case is storing IMAS data progressively in a time loop. You
            can fill the constant and static values only once and progressively append
            the dynamic values calculated in each step of the time loop with
            :meth:`put_slice`.

            .. code-block:: python

                ids = imas.IDSFactory().pf_active() ...  # fill the static data of the
                pf_active IDS here for i in range(N):
                    ... # fill time slice of the pf_active IDS imas_entry.put_slice(ids)
        """
        self._put(ids, occurrence, True)

    def _put(self, ids: IDSToplevel, occurrence: int, is_slice: bool):
        """Actual implementation of put() and put_slice()"""
        if self._dbe_impl is None:
            raise RuntimeError("Database entry is not open.")
        if ids._lazy:
            raise ValueError("Lazy loaded IDSs cannot be used in put or put_slice.")

        # Automatic validation
        disable_validate = os.environ.get("IMAS_AL_DISABLE_VALIDATE")
        if not disable_validate or disable_validate == "0":
            try:
                ids.validate()
            except ValidationError:
                logger.error(
                    "IDS %s is not valid. You can disable automatic IDS validation by "
                    "setting the environment variable IMAS_AL_DISABLE_VALIDATE=1.",
                    ids.metadata.name,
                )
                raise

        ids_name = ids.metadata.name
        # Verify homogeneous_time is set
        time_mode = ids.ids_properties.homogeneous_time
        # TODO: allow unset homogeneous_time and quit with no action?
        if time_mode not in IDS_TIME_MODES:
            raise ValueError("'ids_properties.homogeneous_time' is not set or invalid.")
        # IMAS-3330: automatically set time mode to independent:
        if ids.metadata.type is IDSType.CONSTANT:
            if time_mode != IDS_TIME_MODE_INDEPENDENT:
                logger.warning(
                    "ids_properties/homogeneous_time has been set to 2 for the constant"
                    " IDS %s/%d. Please check the program which has filled this IDS"
                    " since this is the mandatory value for a constant IDS",
                    ids_name,
                    occurrence,
                )
                ids.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
        if is_slice and time_mode == IDS_TIME_MODE_INDEPENDENT:
            raise RuntimeError("Cannot use put_slice with IDS_TIME_MODE_INDEPENDENT.")

        # Set version_put properties (version_put was added in DD 3.22)
        if hasattr(ids.ids_properties, "version_put"):
            version_put = ids.ids_properties.version_put
            version_put.data_dictionary = self._ids_factory._version
            version_put.access_layer = self._dbe_impl.access_layer_version()
            version_put.access_layer_language = f"imas {imas.__version__}"

        self._dbe_impl.put(ids, occurrence, is_slice)

    def delete_data(self, ids_name: str, occurrence: int = 0) -> None:
        """Delete the provided IDS occurrence from this IMAS database entry.

        Args:
            ids_name: Name of the IDS to delete from the backend.
            occurrence: Which occurrence of the IDS to delete.
        """
        if self._dbe_impl is None:
            raise RuntimeError("Database entry is not open.")
        self._dbe_impl.delete_data(ids_name, occurrence)

    @overload
    def list_all_occurrences(
        self, ids_name: str, node_path: None = None
    ) -> List[int]: ...

    @overload
    def list_all_occurrences(
        self, ids_name: str, node_path: str
    ) -> Tuple[List[int], List[IDSBase]]: ...

    def list_all_occurrences(self, ids_name, node_path=None):
        """List all non-empty occurrences of an IDS

        Note: this is only available with Access Layer core version 5.1 or newer.

        Args:
            ids_name: name of the IDS (e.g. "magnetics", "core_profiles" or
                "equilibrium")
            node_path: path to a Data-Dictionary node (e.g. "ids_properties/comment",
                "code/name", "ids_properties/provider").

        Returns:
            tuple or list:
                When no ``node_path`` is supplied, a (sorted) list with non-empty
                occurrence numbers is returned.

                When ``node_path`` is supplied, a tuple ``(occurrence_list,
                node_content_list)`` is returned. The ``occurrence_list`` is a (sorted)
                list of non-empty occurrence numbers. The ``node_content_list`` contains
                the contents of the node in the corresponding occurrences.

        Example:
            .. code-block:: python

                dbentry = imas.DBEntry(uri, "r")
                occurrence_list, node_content_list = \\
                    dbentry.list_all_occurrences("magnetics", "ids_properties/comment")
                dbentry.close()
        """
        if self._dbe_impl is None:
            raise RuntimeError("Database entry is not open.")

        occurrence_list = self._dbe_impl.list_all_occurrences(ids_name)

        if node_path is None:
            return occurrence_list

        node_content_list = [
            self.get(ids_name, occ, lazy=True)[node_path] for occ in occurrence_list
        ]
        return occurrence_list, node_content_list
