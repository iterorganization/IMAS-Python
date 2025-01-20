.. _changelog:

Changelog
=========

What's new in imas-python 1.1.1
-------------------------------

This is a small release that mainly fixes issues related to the recent Data
Dictionary 4.0.0 release.

Bug fixes
'''''''''

- Data Dictionary 4.0.0 compatibility:

  - Fix a bug with ``get_slice`` and ``put_slice`` not correctly slicing data.
  - Update tests and examples. Some were updated to be compatible with both Data
    Dictionary 4.0.0 and 3.42.0. In other cases, the Data Dictionary version is
    now explicitly indicated.

- :issue:`IMAS-5560`: Fix a bug where imas-python would not correctly recognize that
  the UDA backend is used.
- :issue:`IMAS-5541`: Fix a bug when converting a closed contour to Data
  Dictionary version 4.0.0.
- Work around incorrect Data Dictionary 3.x metadata when converting
  ``flux_loop/flux`` in the ``magnetics`` IDS to Data Dictionary version 4.0.0.
- Fix a bug when lazy loading Arrays of Structures that where added in a more
  recent Data Dictionary version than the on-disk data was stored with.


What's new in imas-python 1.1
-----------------------------

New features
''''''''''''

- :ref:`1.1/improved performance`.
- :ref:`1.1/improved conversion`.
- imas-python 1.1 adds support for Identifiers defined by the Data Dictionary. This
  functionality is described in detail in :ref:`Identifiers`.
- Support for the new
  :py:const:`~imaspy.ids_defs.FLEXBUFFERS_SERIALIZER_PROTOCOL` that is
  implemented in Access Layer Core 5.3. This is a much faster and more efficient
  serialization format than the
  :py:const:`~imaspy.ids_defs.ASCII_SERIALIZER_PROTOCOL`. The Flexbuffers
  serializer protocol requires ``imas_core`` version 5.3 or newer. It is the
  default serializer format when it is available. This features is not available
  when the variable :py:const:`~imaspy.ids_defs.FLEXBUFFERS_SERIALIZER_PROTOCOL`
  is set to ``None``.
- Preview feature: :ref:`IMAS netCDF files`. Store IDSs in a self-describing
  netCDF file, which can be used for sharing and/or archiving data.
  
  This feature is in `preview` status, meaning that it may change in upcoming
  minor releases of imas-python.

- Additional utility functions in :py:mod:`imaspy.util`:

  - :py:func:`imaspy.util.tree_iter` can be used to iterate over all nodes inside
    an IDS.
  - :py:func:`imaspy.util.get_parent` can be used to get the parent element of
    an IDS node.
  - :py:func:`imaspy.util.get_time_mode` is a convenience function to get the
    ``ids_properties/homogeneous_time`` value for any node in the IDS.
  - :py:func:`imaspy.util.get_toplevel` returns the IDS Toplevel element for any
    node in the IDS.
  - :py:func:`imaspy.util.is_lazy_loaded` will indicate whether an IDS is lazy
    loaded.
  - :py:func:`imaspy.util.get_full_path` returns the full path (including Array
    of Structure indices) of a node.
  - :py:func:`imaspy.util.get_data_dictionary_version` returns the Data
    Dictionary version for which an IDS was created.

- Add support for IMAS Access Layer Core 5.2 and later. imas-python can now be used
  with just the Access Layer Core package available, the full AL-Python HLI is
  no longer required.

  Since the Access Layer Core is now installable with ``pip`` as well (requires
  access to the git repository on
  `<https://github.com/iterorganization/imas-core>`__), you can install
  ``imas`` and ``imas_core`` in one go with:

  .. code-block:: bash

    pip install 'imas[imas-core] @ git+ssh://git@github.com/iterorganization/imas-core.git'

- A diff tool for IDSs: :py:func:`imaspy.util.idsdiff`.
- Implement ``==`` equality checking for IDS Structures and Arrays of Structures
  (`IMAS-5120 <https://jira.iter.org/browse/IMAS-5120>`__).
- Add option to ignore unknown Data Dictionary versions of data stored in the
  backend.

  During a :py:meth:`~imaspy.db_entry.DBEntry.get` or
  :py:meth:`~imaspy.db_entry.DBEntry.get_slice`, imas-python first reads the version
  of the Data Dictionary that was used to store the IDS. When this version is
  not known to imas-python, an error is raised. This error can now be ignored by
  setting the parameter
  :py:param:`~imaspy.db_entry.DBEntry.get.ignore_unknown_dd_version` to
  ``True``, and imas-python will do its best to load the data anyway.

- A new command line tool exists for analyzing which Data Dictionary fields are
  used in provided Data Entries. This tool is explained in detail in
  :ref:`imas-python Data Entry analysis`.

- Various improvements to the documentation were made.


Breaking changes
''''''''''''''''

.. note::

  We attempt to keep the public API of imas-python stable with minor releases. The
  following breaking change is the result of an upgrade of the IMAS Access Layer.

- Starting with Access Layer 5.2 or newer, the Access Layer will raise
  exceptions when errors occur in the ``imas_core`` layer. For example, when
  attempting to read from non-existing Data Entries or when a Data Entry cannot
  be opened for writing data.

  You may need to update the :py:class:`Exception` classes in ``try/except``
  blocks to the new Exception classes raised by ``imas_core``.

  When using an older version of the Access Layer, the behaviour of imas-python is no
  different than in imas-python 1.0.


Bug fixes
'''''''''

- Fixed a bug in :py:func:`imaspy.util.inspect` when inspecting lazy loaded IDSs.
- Fixed a bug when converting the ``neutron_diagnostics`` IDS to/from Data
  Dictionary version ``3.41.0``.
- Fixed a bug that allowed setting arbitrary attributes on IDS structures. It is
  only allowed to use attributes defined by the Data Dictionary.
- Fixed a bug with :py:func:`~imaspy.ids_toplevel.IDSToplevel.serialize` when
  the IDS is in a non-default Data Dictionary version.
- Fixed a bug when assigning ``nan`` to a FLT_0D, which would lead to a
  confusing and incorrect log message in imas-python 1.0.
- Fixed incorrect oldest supported DD version. Previously imas-python indicated that
  DD ``3.21.1`` was supported, however ``3.22.0`` is the oldest Data Dictionary
  tested (and provided) with imas-python. :py:attr:`imaspy.OLDEST_SUPPORTED_VERSION`
  has been updated to reflect this.
- Fixed a bug when using numpy functions, such as
  :external:py:func:`numpy.isclose` on scalar numbers. Previously an error was
  raised (``TypeError: ufunc 'isfinite' not supported for the input types, and
  the inputs could not be safely coerced to any supported types according to the
  casting rule ''safe''``), now this works as expected.
- Fixed bugs that relied on the presence of the environment variables ``USER``,
  ``PATH`` and ``LD_LIBRARY_PATH``. Although these are defined most of the time
  on Linux systems, they can be empty and this is now handled correctly.



.. _`1.1/improved performance`:

Improved performance
''''''''''''''''''''

- Improved performance of :py:meth:`~imaspy.ids_toplevel.IDSToplevel.validate`.
- Improved creation of imas-python IDS objects. This made filling IDSs and loading
  them with :py:meth:`~imaspy.db_entry.DBEntry.get` /
  :py:meth:`~imaspy.db_entry.DBEntry.get_slice` 10-20% faster.
- Improved the performance of lazy loading. This is most noticeable with the
  ``HDF5`` backend, which is now up to 40x faster than with imas-python 1.0.
- Improved the performance of :py:meth:`~imaspy.db_entry.DBEntry.get` /
  :py:meth:`~imaspy.db_entry.DBEntry.get_slice` /
  :py:meth:`~imaspy.db_entry.DBEntry.put` /
  :py:meth:`~imaspy.db_entry.DBEntry.put_slice` for IDSs with many nested arrays
  of structures. This performance improvement is most noticeable for IDSs with
  filled GGD grids and data structures (up to 25% faster).


.. _`1.1/improved conversion`:

Improved IDS conversion between Data Dictionary versions
''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Converting IDSs between Data Dictionary versions has several improvements for
recent DD versions. Further details on IDS conversion can be found in
:ref:`Conversion of IDSs between DD versions`.

- The imas-python Command Line Interface for converting Data Entries between different
  versions of the Data Dictionary has been improved. See :ref:`Command line tool
  reference` or execute ``imas convert --help`` in a shell for further
  details.

- Add support for multiple renames in an IDS' path.

  For example, in the ``pulse_schedule`` IDS, the node
  ``ec/beam/power_launched/reference`` in Data Dictionary ``3.40.0`` was renamed
  from ``ec/launcher/power/reference/data`` in Data Dictionary ``3.39.0``. This
  use case is now supported by imas-python.

- Automatically convert data between 0D and 1D when possible (`IMAS-5170
  <https://jira.iter.org/browse/IMAS-5170>`__).
  The following type changes are now automatically supported by
  :py:func:`imaspy.convert_ids <imaspy.ids_convert.convert_ids>`:

  - INT_0D to INT_1D
  - FLT_0D to FLT_1D
  - CPX_0D to CPX_1D
  - STR_0D to STR_1D
  - Structure to Array of structures

  See :ref:`Supported conversions` for more details.

- Add data conversion from Data Dictionary version 3.x to Data Dictionary
  version 4.x:

  - Convert changed COCOS definitions: automatically multiply nodes that have
    changed their COCOS definition with ``-1``.
  - Convert changed definition of ``circuit(i1)/connection`` in the
    ``pf_active`` IDS.
  - Convert changed definition of open/closed contours.
  - Convert changed definition of ``space/coordinates_type`` in GGD grid structures.
