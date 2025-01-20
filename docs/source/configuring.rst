Configuring imas-python
=======================

imas-python has a couple of environment variables that can be used to control its behaviour.
This page provides an overview of available variables.

.. note::

    In addition to the listed environment variables, the Access Layer lowlevel also has
    environment variables available to control its behaviour. See the `Access Layer
    documentation
    <https://sharepoint.iter.org/departments/POP/CM/IMDesign/Code%20Documentation/ACCESS-LAYER-doc/python/5.1/conf.html#environment-variables-controlling-access-layer-plugins>`_


``IMAS_LOGLEVEL``
    Sets the log level used by the imas-python logger.
    
    By default (when this environment variable is not set), all log messages of ``INFO``
    or more severe are logged. You may set this to, for example,
    ``IMAS_LOGLEVEL=WARNING``, to suppress some of the log messages.

    See the Python documentation for the :external:py:mod:`logging` module which log
    levels are available.

    .. note::

        This environment variable is read when the ``imas`` library is initialized
        during the first ``import imas``. Changing it afterwards has no effect, but
        you can use :external:py:meth:`logging.getLogger("imas").setLevel(...)
        <logging.Logger.setLevel>` to change the log level programmatically.


``IMAS_DISABLE_NC_VALIDATE``
    Disables validation of netCDF files when loading an IDS from an IMAS netCDF file.

    .. caution::
        Disabling the validation may lead to errors when reading data from an IMAS netCDF file.

``IMAS_VERSION``
    Sets :ref:`The default Data Dictionary version` to use.


Environment variables shared with the IMAS Python HLI
-----------------------------------------------------

``IMAS_AL_DISABLE_VALIDATE``
    By default, imas-python :ref:`validates <IDS validation>` IDSs to check that all data is
    consistent with their coordinates during a :py:meth:`~imas.db_entry.DBEntry.put`
    or :py:meth:`~imas.db_entry.DBEntry.put_slice`.

    Setting ``IMAS_AL_DISABLE_VALIDATE=1`` disables this validation.

``IMAS_AL_SERIALIZER_TMP_DIR``
    Specify the path to storing temporary data during
    :py:meth:`~imas.ids_toplevel.IDSToplevel.serialize` and
    :py:meth:`~imas.ids_toplevel.IDSToplevel.deserialize`.
    
    If it is not set, the default location ``/dev/shm/`` or the current working
    directory will be chosen.
