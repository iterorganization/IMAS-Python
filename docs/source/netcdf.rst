.. _`IMAS netCDF files`:

IMAS netCDF files \& Xarray
===========================

.. toctree::
    :hidden:

    netcdf/conventions


IMAS-Python supports reading IDSs from and writing IDSs to IMAS netCDF files. This
feature is currently in alpha status, and its functionality may change in
upcoming (minor) releases of IMAS-Python.

A detailed description of the IMAS netCDF format and conventions can be found on
the :ref:`IMAS conventions for the netCDF data format` page.

Reading from and writing to netCDF files uses the same :py:class:`imas.DBEntry
<imas.db_entry.DBEntry>` API as reading and writing to Access Layer backends.
If you provide a path to a netCDF file (ending with ``.nc``) the netCDF backend
will be used for :py:meth:`~imas.db_entry.DBEntry.get` and
:py:meth:`~imas.db_entry.DBEntry.put` calls. See the below example:

.. code-block:: python
    :caption: Use DBEntry to write and read IMAS netCDF files

    import imas

    cp = imas.IDSFactory().core_profiles()
    cp.ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_INDEPENDENT
    cp.ids_properties.comment = "Test IDS"

    # This will create the `test.nc` file and stores the core_profiles IDS in it
    with imas.DBEntry("test.nc", "w") as netcdf_entry:
        netcdf_entry.put(cp)

    # Reading back:
    with imas.DBEntry("test.nc", "r") as netcdf_entry:
        cp2 = netcdf_entry.get("core_profiles")

    imas.util.print_tree(cp2)


Implemented features of a netCDF ``DBEntry``
--------------------------------------------

A netCDF ``DBEntry`` doesn't implement all features that are supported by
``imas_core``. The following table provides an overview of the implemented
features that are supported by DBEntries using ``imas_core`` respectively
``netCDF``:

.. list-table::
    :header-rows: 1
    
    * - Feature
      - ``imas_core``
      - ``netCDF``
    * - :ref:`Lazy loading`
      - Yes
      - Yes
    * - :ref:`Automatic conversion between DD versions <Conversion of IDSs between DD versions>`
      - When reading and writing
      - When reading
    * - ``get_slice`` / ``put_slice``
      - Yes
      - Not implemented
    * - ``get_sample``
      - Yes (requires ``imas_core >= 5.4.0``)
      - Not implemented

.. _`Using IMAS netCDF files with 3rd-party tools`:

Using IMAS netCDF files with 3rd-party tools
--------------------------------------------

The netCDF files produces by IMAS-Python can be read with external tools. In this
section we will show how to load data with the `xarray
<https://docs.xarray.dev/en/stable/index.html>`__ package.

Let's first create a small netCDF file in the current working directory based on
the IMAS-Python training data:

.. code-block:: python
    :caption: Store ``core_profiles`` training data in a netCDF file

    import imas.training

    # Open the training entry
    with imas.training.get_training_db_entry() as training_entry:
        # Load the core_profiles IDS
        core_profiles = training_entry.get("core_profiles")
        # Open a netCDF entry to store this IDS in:
        with imas.DBEntry("core_profiles.nc", "w") as nc:
            nc.put(core_profiles)

If you execute this code snippet, you will find a file ``core_profiles.nc`` in
your directory. Let's open this file with ``xarray.load_dataset``:

.. code-block:: python
    :caption: Load ``core_profiles`` training data with ``xarray`` and create a plot

    import xarray
    from matplotlib import pyplot as plt

    # Load the dataset. Note the group="core_profiles/0" indicating we want to
    # load the default occurrence of the core_profiles IDS:
    ds = xarray.load_dataset("core_profiles.nc", group="core_profiles/0")

    # Plot j_tor with time on the x-axis and rho_tor_norm on the y-axis
    j_tor = ds["profiles_1d.j_tor"]
    j_tor.plot(x="time", y="profiles_1d.grid.rho_tor_norm")
    plt.show()


.. important::

    IMAS netCDF files store IDSs and their occurrences in *groups* inside the
    netCDF file. ``xarray`` will, by default, only look for data in the *root
    group* of the file. If you don't provide the ``group`` parameter
    (``"<ids_name>/<occurrence>"``, see above example), you will find an empty
    dataset:

    .. code-block:: python

        >>> xarray.load_dataset("core_profiles.nc")
        <xarray.Dataset> Size: 0B
        Dimensions:  ()
        Data variables:
            *empty*
        Attributes:
            Conventions:              IMAS
            data_dictionary_version:  3.41.0


Validating an IMAS netCDF file
------------------------------

IMAS netCDF files can be validated with IMAS-Python through the command line ``imas
validate_nc <filename>``. See also :ref:`IMAS-Python Command Line tool` or type
``imas validate_nc --help`` in a command line.


.. _`Convert IMAS-Python IDSs directly to Xarray Datasets`:

Convert IMAS-Python IDSs directly to Xarray Datasets
----------------------------------------------------

In the section :ref:`Using IMAS netCDF files with 3rd-party tools`, we showed
how to open an IMAS netCDF file with Xarray. However, IMAS-Python IDSs can also
be converted directly to Xarray ``Dataset``\ s with
:py:func:`imas.util.to_xarray`.

This method can be used to convert a full IDS to an Xarray ``Dataset``, or only
specific paths inside the IDS. The latter variant can also be combined with
:ref:`lazy loading`. We'll show a small example below:

.. code-block:: python
    :caption: Converting a lazy loaded IDS to Xarray

    import imas.training

    # Open the training entry
    with imas.training.get_training_db_entry() as training_entry:
        # Lazy load the core_profiles IDS
        core_profiles = training_entry.get("core_profiles", lazy=True)
        # Load the average ion temperature and all coordinate data
        xrds = imas.util.to_xarray(core_profiles, "profiles_1d.t_i_average")
        # All relevant data is now loaded from the data entry into the xarray
        # Dataset. We close the data entry by exiting the with-statement.

    # Inspect what's inside the dataset
    print(xrds.data_vars)
    # Data variables:
    #   profiles_1d.t_i_average

    # Included coordinates depends on the used Data Dictionary version
    print(xrds.coords)
    # Coordinates:  (with DD 4.0.0)
    # * time
    #   profiles_1d.grid.area
    #   profiles_1d.grid.volume
    #   profiles_1d.grid.rho_tor
    #   profiles_1d.grid.rho_tor_norm
    #   profiles_1d.grid.psi
