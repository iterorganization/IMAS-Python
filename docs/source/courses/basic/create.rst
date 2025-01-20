Create with imas-python
=======================

In this section of the training, we will have a look at creating (and filling) IDSs from
scratch.

Create an empty IDS
-------------------

Empty IDSs in imas-python are created by the :py:meth:`~imas.ids_factory.IDSFactory.new`
method of an :py:class:`~imas.ids_factory.IDSFactory`.

.. note::
    New IDSs can also be created by calling :code:`IDSFactory().<ids_name>()`, similar
    to how new IDSs are constructed in the Access Layer.


Exercise 1
''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        Create an empty ``core_profiles`` IDS.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/create_core_profiles.py
            :end-before: # Set properties


Populate fields
---------------

Now we have an empty IDS, we can start filling fields. For this exercise we will
populate the following fields:

- ``ids_properties.homogeneous_time``, which we will set to the constant
  :py:const:`~imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS`. This flags that this IDS is in
  homogeneous time mode, meaning that all time-dependent quantities use the root
  ``time`` as their coordinate.
- ``ids_properties.comment``, where we can describe this IDS.
- ``ids_properties.creation_date``, which we need to set to today's date.
- :code:`time = [1.0, 2.5, 4.0]`
- ``profiles_1d`` is an array of structures, with one structure for each time slice. We
  need to resize it to match the size of the ``time`` array.
- For each ``profiles_1d`` we generate an electron temperature array and store it in
  ``profiles_1d[index].electrons.temperature``.


Exercise 2
''''''''''

.. md-tab-set::
    
    .. md-tab-item:: Exercise

        Fill the ``core_profiles`` IDS with the fields as described above.


    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/create_core_profiles.py
            :start-at: # Set properties
            :end-before: # Validate the IDS for consistency

        .. note::

            Observe that we can assign a Python list to ``cp.time``. imas-python will
            automatically convert it to a numpy array.


Sanity check the IDS
--------------------

Before we store the IDS to disk, it is good practice to :ref:`validate the IDS <IDS
validation>`. When the IDS passes validation, you know that all filled quantities are
consistent with their coordinates (because, what is the data worth if its coordinates
are not provided?).


Exercise 3
''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        Validate the just-filled IDS.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/create_core_profiles.py
            :start-at: # Validate the IDS for consistency
            :end-before: # Fill in the missing rho_tor_norm coordinate

You should find that the IDS validation fails. Why?

.. admonition:: Solution
    :collapsible:

    We set the electron temperature, but we didn't fill its coordinate ``rho_tor_norm``!
    The IDS validation reports an inconsistency between the data and coordinate size:
    ``Dimension 1 of element `profiles_1d[0].electrons.temperature` has incorrect size
    64. Expected size is 0 (size of coordinate `profiles_1d[0].grid.rho_tor_norm`).``


Exercise 4
''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        Fix the coordinate consistency error.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/create_core_profiles.py
            :start-at: # Fill in the missing rho_tor_norm coordinate
            :end-before: # Create a new data entry for storing the IDS


Store the IDS on disk
---------------------

Now we have created, filled and validated an IDS, the only thing left is to store it to
disk. Like loading IDSs, storing IDSs is achieved through the
:py:class:`~imas.db_entry.DBEntry` class. After constructing a ``DBEntry`` object, you
need to :py:meth:`~imas.db_entry.DBEntry.create` the data entry on-disk before you can
:py:meth:`~imas.db_entry.DBEntry.put` the IDS to disk.

.. note::
    For this exercise we will use the ASCII backend. Although it doesn't have the best
    performance or features, it is available in all builds of the Access Layer. For
    production usage, it is recommended to use the HDF5 or MDSplus backends.


Exercise 5
''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        Store the IDS to disk.

        The recommended parameters for this exercise are::

            backend = imas.ids_defs.ASCII_BACKEND
            database = "imas-course"
            pulse = 1
            run = 1

        After a successful ``put``, the ids file will be created. 
        this file can be found under
        ``~/public/imasdb/imas-course/3/1/1/core_profiles.ids`` 

        .. hint::
            :collapsible:

            The signature of :meth:`~imas.db_entry.DBEntry()` is: ``DBEntry(backend, database, pulse, run)``

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/create_core_profiles.py
            :start-at: # Create a new data entry for storing the IDS

Summary
-------

Congratulations for completing this section of the course. You have:

- Created an empty ``core_profiles`` IDS
- Filled some data fields of this IDS
- Ensured consistency of coordinates in the IDS
- Stored the newly created IDS to disk

.. md-tab-set::

    .. md-tab-item:: Summary

        Click on the tabs to see the complete source, combining all exercises.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/create_core_profiles.py
