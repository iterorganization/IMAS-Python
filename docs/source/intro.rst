.. _`imas-python 5 minute introduction`:

imas-python 5 minute introduction
---------------------------------

.. contents:: Contents
    :local:
    :depth: 1


Verify your IMAS installation
'''''''''''''''''''''''''''''

Before continuing, verify that your imas install is working. Check the
:ref:`Installing imas-python` page for installation instructions if below fails for
you. Start python and import imas. Note that the version in below output may
be outdated.

.. code-block:: python

    >>> import imas
    >>> print(imas.__version__)
    1.0.0

.. note::

    If you have an imas-python install without the IMAS Access Layer, importing
    imas-python will display an error message. You can still use imas-python, but not all
    functionalities are available.


Create and use an IDS
'''''''''''''''''''''

To create an IDS, you must first make an :py:class:`~imas.ids_factory.IDSFactory`
object. The IDS factory is necessary for specifying which version of the IMAS Data
Dictionary you want to use. If you don't specify anything, imas-python uses the same Data
Dictionary version as the loaded IMAS environment, or the latest available version. See
:ref:`Using multiple DD versions in the same environment` for more information
on different Data Dictionary versions.

.. code-block:: python

    >>> import imas
    >>> import numpy as np
    >>> ids_factory = imas.IDSFactory()
    13:26:47 [INFO] Parsing data dictionary version 3.38.1 @dd_zip.py:127
    >>> # Create an empty core_profiles IDS
    >>> core_profiles = ids_factory.core_profiles()

We can now use this ``core_profiles`` IDS and assign some data to it:

.. code-block:: python

    >>> core_profiles.ids_properties.comment = "Testing imas-python"
    >>> core_profiles.ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS
    >>> # array quantities are automatically converted to the appropriate numpy arrays
    >>> core_profiles.time = [1, 2, 3]
    >>> # the python list of ints is converted to a 1D array of floats
    >>> core_profiles.time
    <IDSNumericArray (IDS:core_profiles, time, FLT_1D)>
    numpy.ndarray([1., 2., 3.])
    >>> # resize the profiles_1d array of structures to match the size of `time`
    >>> core_profiles.profiles_1d.resize(3)
    >>> len(core_profiles.profiles_1d)
    3
    >>> # assign some data for the first time slice
    >>> core_profiles.profiles_1d[0].grid.rho_tor_norm = [0, 0.5, 1.0]
    >>> core_profiles.profiles_1d[0].j_tor = [0, 0, 0]

As you can see in the example above, imas-python automatically checks the data you try to
assign to an IDS with the data type specified in the Data Dictionary. When
possible, your data is automatically converted to the expected type. You will
get an error message if this is not possible:

.. code-block:: python

    >>> core_profiles.time = "Cannot be converted"
    ValueError: could not convert string to float: 'Cannot be converted'
    >>> core_profiles.time = 1-1j
    TypeError: can't convert complex to float
    >>> core_profiles.ids_properties.source = 1-1j  # automatically converted to str
    >>> core_profiles.ids_properties.source.value
    '(1-1j)'


Store an IDS to disk
''''''''''''''''''''

.. note::

    - This functionality requires the IMAS Access Layer.
    - This API will change when imas-python is moving to Access Layer 5 (expected Q2
      2023).

To store an IDS to disk, we need to indicate the following information to the
IMAS Access Layer. Please check the `IMAS Access Layer documentation
<https://imas.iter.org/>`_ for more information on this.

- Which backend to use (e.g. MDSPLUS or HDF5)
- ``tokamak`` (also known as database)
- ``pulse``
- ``run``

In imas-python you do this as follows:

.. code-block:: python

    >>> # Create a new IMAS data entry for storing the core_profiles IDS we created earlier
    >>> # Here we specify the backend, database, pulse and run
    >>> dbentry = imas.DBEntry(imas.ids_defs.HDF5_BACKEND, "TEST", 10, 2)
    >>> dbentry.create()
    >>> # now store the core_profiles IDS we just populated
    >>> dbentry.put(core_profiles)

.. image:: imas_structure.png


Load an IDS from disk
'''''''''''''''''''''

.. note::

    - This functionality requires the IMAS Access Layer.
    - This API will change when imas-python is moving to Access Layer 5 (expected Q2
      2023).

To load an IDS from disk, you need to specify the same information as
when storing the IDS (see previous section). Once a data entry is opened, you
can use ``<IDS>.get()`` to load IDS data from disk: 

.. code-block:: python

    >>> # Now load the core_profiles IDS back from disk
    >>> dbentry2 = imas.DBEntry(imas.ids_defs.HDF5_BACKEND, "TEST", 10, 2)
    >>> dbentry2.open()
    >>> core_profiles2 = dbentry2.get("core_profiles")
    >>> print(core_profiles2.ids_properties.comment.value)
    Testing imas-python
