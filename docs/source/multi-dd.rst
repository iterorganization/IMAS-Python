.. _`Using multiple DD versions in the same environment`:

Using multiple DD versions in the same environment
==================================================

Whereas the default IMAS High Level Interface is built for a single Data Dictionary
version, IMAS-Python can transparently handle multiple DD versions.

By default, IMAS-Python uses the same Data Dictionary version as the loaded IMAS environment
is using, as specified by the environment variable ``IMAS_VERSION``. If no IMAS
environment is loaded, the last available DD version is used.

You can also explicitly specify which IMAS version you want to use when constructing a
:py:class:`~imas.db_entry.DBEntry` or :py:class:`~imas.ids_factory.IDSFactory`. For
example:

.. code-block:: python
    :caption: Using non-default IMAS versions.

    import imas

    factory_default = imas.IDSFactory()  # Use default DD version
    factory_3_32_0 = imas.IDSFactory("3.32.0")  # Use DD version 3.32.0

    # Will write IDSs to the backend in DD version 3.32.0
    dbentry = imas.DBEntry("imas:hdf5?path=dd3.32.0-output/", "w", dd_version="3.32.0")
    dbentry.create()

.. seealso:: :ref:`multi-dd training`


.. _`Conversion of IDSs between DD versions`:

Conversion of IDSs between DD versions
--------------------------------------

IMAS-Python can convert IDSs between different versions of the data dictionary. This uses the
"non-backwards compatible changes" metadata from the DD definitions. There are
two conversion modes:

1.  Automatic conversion: this is handled when reading or writing data
    (:py:meth:`~imas.db_entry.DBEntry.get`/:py:meth:`~imas.db_entry.DBEntry.get_slice`,
    :py:meth:`~imas.db_entry.DBEntry.put`/:py:meth:`~imas.db_entry.DBEntry.put_slice`).

    The DBEntry class automatically converts IDSs to the requested version:

    - When doing a ``put`` or ``put_slice``, the provided IDS is automatically converted to
      the target version of the DBEntry when putting to disk.
    - When doing a ``get`` or ``get_slice``, the IDS is automatically converted from the
      data dictionary version it was stored in (by checking
      ``ids_properties/version_put/data_dictionary``) to the requested target version.
  
    .. caution::

      The automatic conversion doesn't provide feedback when data cannot be converted
      between two versions of the data dictionary. Any incompatibilities between versions
      are silently ignored.

2.  Explicit conversion: this is achieved with a call to
    :py:func:`imas.convert_ids <imas.ids_convert.convert_ids>`.

Automatic conversion is faster when reading data (up to a factor 2, depending on
the backend and the stored data), but it doesn't support all conversion logic
(see :ref:`Supported conversions`).


.. rubric:: Recommendations for reading data

-   Use automatic conversion when converting IDSs between Data Dictionary
    versions that have the same major version, unless you require a feature that
    is not supported by the automatic conversion.
-   Use explicit conversion (see the example below) when converting IDSs between
    different major versions of the Data Dictionary.
-   If you're often reading the same data from a different DD version, it may
    be more efficient to convert the data to your DD version, store it and then
    use it. This avoids conversion every time you read the data.

    Converting an entire Data Entry can also be done with the IMAS-Python command
    line interface. See :ref:`IMAS-Python Command Line tool`.


Explicit conversion
'''''''''''''''''''

.. code-block:: python
    :caption: Explicitly convert data when reading from disk

    import imas

    entry = imas.DBEntry("<URI to data>", "r")

    # Disable automatic conversion when reading the IDS with autoconvert=False
    ids = entry.get("<ids name>", autoconvert=False)
    # Explicitly convert the IDS to the target version
    ids = imas.convert_ids(ids, "<target DD version>")


.. code-block:: python
    :caption: Convert an IDS to a different DD version

    import imas

    # Create a pulse_schedule IDS in version 3.23.0
    ps = imas.IDSFactory("3.25.0").new("pulse_schedule")
    ps.ec.antenna.resize(1)
    ps.ec.antenna[0].name = "IDS conversion test"

    # Convert the IDS to version 3.30.0
    ps330 = imas.convert_ids(ps, "3.30.0")
    # ec.antenna was renamed to ec.launcher between 3.23.0 and 3.30.0
    print(len(ps330.ec.launcher))  # 1
    print(ps330.ec.launcher[0].name.value)  # IDS conversion test

.. note::

    Not all data may be converted. For example, when an IDS node is removed between DD
    versions, the corresponding data is not copied. IMAS-Python provides logging to indicate
    when this happens.

.. rubric:: DD3 -> DD4 special rule: name + identifier -> description + name (GH#59)

IMAS‑Python implements an additional explicit conversion rule (see GH#59) to improve 
migration of Machine Description parts of IDSs when moving from major version 3 to 4. 
The rule targets simple sibling pairs on the same parent that provide both a "name" 
and an "identifier" field and that are NOT part of an "identifier structure" (the 
parent must not also have an "index" sibling). When applicable the rule performs the 
following renames during explicit DD3->DD4 conversion:

- DD3: parent/name       -> DD4: parent/description
- DD3: parent/identifier -> DD4: parent/name

The conversion is applied only when the corresponding target fields exist in the
DD4 definition and when no earlier mapping already covers the same paths. This
is performed by the explicit conversion machinery (for example via
imas.convert_ids or DBEntry explicit conversion) and is not guaranteed to be
applied by automatic conversion when reading/writing from a backend.

In some cases like the one above, reverse conversion is also allowed(DD 4.0.0 -> 3.41.1)

.. _`Supported conversions`:

Supported conversions
'''''''''''''''''''''

The following table shows which conversions are supported by the automatic and
explicit conversion mechanisms.

.. csv-table:: Supported conversions for Non-Backwards-Compatible (NBC) changes
  :header: , Explicit conversion, Automatic conversion
  
  Renames [#rename]_, Yes, Yes
  Type change: structure to array of structure (or reverse), Yes [#aos]_, No [#ignore_type_change]_
  Type change: INT_0D to INT_1D (or reverse), Yes [#0d1d]_, No [#ignore_type_change]_
  Type change: FLT_0D to FLT_1D (or reverse), Yes [#0d1d]_, No [#ignore_type_change]_
  Type change: CPX_0D to CPX_1D (or reverse), Yes [#0d1d]_, No [#ignore_type_change]_
  Type change: STR_0D to STR_1D (or reverse), Yes [#0d1d]_, No [#ignore_type_change]_
  Type change: FLT_0D to INT_0D (or reverse), Yes [#flt_int]_, No [#ignore_type_change]_
  Other type changes, No [#ignore_type_change]_, No [#ignore_type_change]_

.. csv-table:: Supported data conversions between DD major version 3 and major version 4
  :header: , Explicit conversion, Automatic conversion

  Changed COCOS definition, Yes, No
  Changed definition of ``circuit(i1)/connection`` in ``pf_active``, Yes, No
  Changed definition of open/closed contours, Yes, No
  Changed definition of ``space/coordinates_type`` in GGD grids, Yes, No
  Migrate obsolescent ``ids_properties/source`` to ``ids_properties/provenance``, Yes, No
  Convert the multiple time-bases in the ``pulse_schedule`` IDS [#ps3to4]_, Yes, No
  Convert name + identifier -> description + name, Yes, Yes
  Convert equilibrium ``boundary\_[secondary\_]separatrix`` to ``contour_tree`` [#contourtree]_, Yes, No

.. [#rename] Quantities which have been renamed between the two DD versions. For
  example, the ``ec/beam`` Array of Structures in the ``pulse_schedule`` IDS,
  was named ``ec/antenna`` before DD version ``3.26.0`` and ``ec/launcher``
  between versions ``3.26.0`` and ``3.40.0``.

.. [#aos] Conversion from a structure to an array of structures is handled by
  resizing the Array of Structures to size 1, and copying the values inside the
  source structure to the target Array of Structures.

  The reverse is supported when the size of the Array of Structures is 1. A
  warning is logged if more than 1 AoS element is present.

.. [#0d1d] Conversion from a 0D type to a 1D type is handled by creating a 1D
  array with 1 element with the value of the original 0D node. For example,
  converting the FLT_0D ``1.23`` to a FLT_1D results in the numpy array
  ``[1.23]``.

  The reverse is supported when the size of the 1D array is 1. A warning is
  logged if the 1D array has more elements.

.. [#flt_int] Data is only converted from FLT_0D to INT_0D when the floating
    point number can be exactly represented by an integer. For example ``123.0
    -> 123``. Data is not copied and a warning is logged when this is not the
    case.

.. [#ignore_type_change] These type changes are not supported. Quantities in the
    destination IDS will remain empty.

.. [#ps3to4] In Data Dictionary 3.39.0 and older, all dynamic quantities in the
    ``pulse_schedule`` IDS had their own time array. In DD 4.0.0 this was
    restructured to one time array per component (for example `ec/time
    <https://imas-data-dictionary.readthedocs.io/en/latest/generated/ids/pulse_schedule.html#pulse_schedule-ec-time>`__).
    This migration constructs a common time base per subgroup, and interpolates
    the dynamic quantities within the group to the new time base. Resampling
    uses `previous neighbour` interpolation for integer quantities, and linear
    interpolation otherwise. See also:
    https://github.com/iterorganization/IMAS-Python/issues/21.

.. [#contourtree] Fills the `contour_tree
    <https://imas-data-dictionary.readthedocs.io/en/latest/generated/ids/equilibrium.html#equilibrium-time_slice-contour_tree>`__
    in the ``equilibrium`` IDS based on data in the ``boundary_separatrix`` and
    ``boundary_secondary_separatrix`` structures from DD3. See also:
    https://github.com/iterorganization/IMAS-Python/issues/60. 


.. _`Loading IDSs from a different major version`:

Loading IDSs from a different major version
-------------------------------------------

If you try to load an IDS that was stored in a different major version of the DD than
you are using, IMAS-Python will raise a runtime error, for example:

.. code-block:: text

  On-disk data is stored in DD 3.39.1 which has a different major version than the
  requested DD version (4.0.0). IMAS-Python will not automatically convert this
  data for you.

You need to explicitly convert the data, which you can do as follows:

.. code-block:: python

  # Opened data entry
  entry = imas.DBEntry(...)

  # A plain get, or get_slice will raise a RuntimeError when the data is stored in
  # a different major version of the DD:
  # entry.get("equilibrium")

  # So instead, we'll load the IDS in the DD version it is stored on disk
  tmp_eq = entry.get("equilibrium", autoconvert=False)
  # And explicitly convert it to the target version
  equilibrium = imas.convert_ids(tmp_eq, entry.dd_version)


.. _`Storing IDSs with a different major version`:

Storing IDSs with a different major version
-------------------------------------------

If you try to put an IDS that was created for a different major version of the DD than
the Data Entry you want to store it in, IMAS-Python raise a runtime error, for example:

.. code-block:: text

  Provided IDS uses DD 3.42.2 which has a different major version than the Data
  Entry (4.0.0). IMAS-Python will not automatically convert this data for you.

You need to explicitly convert the data, which you can do as follows:

.. code-block:: python

  # IDS with data, in DD 3.42.2
  equilibrium = imas.IDSFactory("3.42.2").equilibrium()
  ...

  # Data Entry uses DD 4.0.0
  with imas.DBEntry(uri, "w", dd_version="4.0.0") as entry:
      # This put would raise a runtime error, because the major version of the IDS
      # and the DBEntry don't match:
      # entry.put(equilibrium)

      # So instead, we'll explicitly convert the IDS and put that one
      entry.put(imas.convert_ids(equilibrium, entry.dd_version))



.. _`DD background`:

Background information
----------------------

Since IMAS-Python needs to have access to multiple DD versions it was chosen to
bundle these with the code at build-time, in setup.py. If a git clone of the
Data Dictionary succeeds, the setup tools automatically download saxon and
generate ``IDSDef.xml`` for each of the tagged versions in the DD git
repository. These are then gathered into ``IDSDef.zip``, which is
distributed inside the IMAS-Python package.

To update the set of data dictionaries new versions can be added to the zipfile.
A reinstall of the package will ensure that all available versions are included
in IMAS-Python. Additionally an explicit path to an XML file can be specified, which
is useful for development.

Automated tests have been provided that check the loading of all of the DD
versions tagged in the data-dictionary git repository.


Data Dictionary definitions
'''''''''''''''''''''''''''

The Data Dictionary definitions used by IMAS-Python are provided by the `IMAS Data
Dictionaries <http://pypi.org/project/imas-data-dictionaries/>`__ package.
Please update this package if you need a more recent version of the data dictionary. For
example, using ``pip``:

.. code-block:: bash

  pip install --upgrade imas-data-dictionaries
