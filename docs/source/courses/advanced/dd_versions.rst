.. _`multi-dd training`:

Working with multiple data dictionary versions
==============================================

Contrary to most high level interface for IMAS, imas-python code is not tied to a specific
version of the Data Dictionary. In this lesson we will explore how imas-python handles
different DD versions (including development builds of the DD), and how we can convert
IDSs between different versions of the Data Dictionary.

.. note::
    Most of the time you won't need to worry about DD versions and the default imas-python
    behaviour should be fine.


.. _`The default Data Dictionary version`:

The default Data Dictionary version
-----------------------------------

In the other training lessons, we didn't explicitly work with Data Dictionary versions.
Therefore imas-python was always using the `default` DD version. Let's find out what that
version is:


.. _`dd version exercise 1`:

Exercise 1: The default DD version
''''''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Create an :py:class:`imas.IDSFactory() <imas.ids_factory.IDSFactory>`.
        2.  Print the version of the DD that is used.
        3.  Create an empty IDS with this IDSFactory (any IDS is fine) and print the
            DD version of the IDS, see
            :py:meth:`~imas.util.get_data_dictionary_version`. What do you notice?
        4.  Create an :py:class:`imas.DBEntry <imas.db_entry.DBEntry>`, you may use
            the :py:attr:`MEMORY_BACKEND <imas.ids_defs.MEMORY_BACKEND>`. Print the
            DD version that is used. What do you notice?

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/dd_versions.py

Okay, so now you know what your default DD version is. But how is it determined? imas-python
first checks if you have an IMAS environment loaded by checking the environment variable
``IMAS_VERSION``. If you are on a cluster and have used ``module load IMAS`` or similar,
this environment variable will indicate what data dictionary version this module is
using. imas-python will use that version as its default.

If the ``IMAS_VERSION`` environment is not set, imas-python will take the newest version of
the Data Dictionary that came bundled with it. Which brings us to the following topic:


Bundled Data Dictionary definitions
-----------------------------------

imas-python comes bundled [#DDdefs]_ with many versions of the Data Dictionary definitions.
You can find out which versions are available by calling
:py:meth:`imas.dd_zip.dd_xml_versions`.


Converting an IDS between Data Dictionary versions
--------------------------------------------------

Newer versions of the Data Dictionary may introduce changes in IDS definitions. Some
things that could change:

-   Introduce a new IDS node
-   Remove an IDS node
-   Change the data type of an IDS node
-   Rename an IDS node

imas-python can convert between different versions of the DD and will migrate the data as
much as possible. Let's see how this works in the following exercise.


Exercise 2: Convert an IDS between DD versions
''''''''''''''''''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        In this exercise we will work with a really old version of the data dictionary
        for the ``pulse_schedule`` IDS because a number of IDS nodes were renamed for
        this IDS.

        1.  Create an :py:class:`imas.IDSFactory() <imas.ids_factory.IDSFactory>`
            for DD version ``3.25.0``.
        2.  Create a ``pulse_schedule`` IDS with this IDSFactory and verify that it is
            using DD version ``3.25.0``.
        3.  Fill the IDS with some test data:

            .. literalinclude:: imas_snippets/ids_convert.py
                :start-after: # 3.
                :end-before: # 4.
        
        4.  Use :py:func:`imas.convert_ids <imas.ids_convert.convert_ids>` to
            convert the IDS to DD version 3.39.0. The ``antenna`` structure that we
            filled in the old version of the DD has since been renamed to ``launcher``,
            and the ``launching_angle_*`` structures to ``steering_angle``. Check that
            imas-python has converted the data successfully (for example with
            :py:func:`imas.util.print_tree`).
        5.  By default, imas-python creates a shallow copy of the data, which means that the
            underlying data arrays are shared between the IDSs of both versions. Update
            the ``time`` data of the original IDS (for example:
            :code:`pulse_schedule.time[1] = 3`) and print the ``time`` data of the
            converted IDS. Are they the same?

            .. note::

                :py:func:`imas.convert_ids <imas.ids_convert.convert_ids>` has an
                optional keyword argument ``deep_copy``. If you set this to ``True``,
                the converted IDS will not share data with the original IDS.

        6.  Update the ``ids_properties/comment`` in one version and print it in the
            other version. What do you notice?
        7.  Sometimes data cannot be converted, for example when a node was added or
            removed, or when data types have changed. For example, set
            ``pulse_schedule.ec.antenna[0].phase.reference_name = "Test refname"`` and
            perform the conversion to DD 3.39.0 again. What do you notice?

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/ids_convert.py


.. _`Automatic conversion between DD versions`:

Automatic conversion between DD versions
----------------------------------------

When loading data (with :py:meth:`~imas.db_entry.DBEntry.get` or
:py:meth:`~imas.db_entry.DBEntry.get_slice`) or storing data (with
:py:meth:`~imas.db_entry.DBEntry.put` or
:py:meth:`~imas.db_entry.DBEntry.put_slice`), imas-python automatically converts the DD
version for you. In this section we will see how that works.


The ``DBEntry`` DD version
''''''''''''''''''''''''''

A :py:class:`~imas.db_entry.DBEntry` object is tied to a specific version of the Data
Dictionary. We have already briefly seen this in :ref:`dd version exercise 1`.

The DD version can be selected when constructing a new ``DBEntry`` object, through the
:py:param:`~imas.db_entry.DBEntry.__init__.dd_version` or
:py:param:`~imas.db_entry.DBEntry.__init__.xml_path` (see also :ref:`Using custom
builds of the Data Dictionary`) parameters. If you provide neither, the default DD
version is used.

When storing IDSs (``put`` or ``put_slice``), the ``DBEntry`` always converts the data
to its version before writing it to the backend. When loading IDSs (``get`` or
``get_slice``) an option exists to disable autoconversion. Let's see in the following
two exercises how this works exactly.


Exercise 3: Automatic conversion when storing IDSs
''''''''''''''''''''''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``core_profiles`` IDS. You can refresh how to
            do this in the following section of the basic training material: :ref:`Open
            an IMAS database entry`.
        2.  Print the DD version for the loaded ``core_profiles`` IDS.
        3.  Create a new ``DBEntry`` with DD version ``3.37.0``.
            
            .. code-block:: python

                new_entry = imas.DBEntry(
                    imas.ids_defs.MEMORY_BACKEND, "test", 0, 0, dd_version="3.37.0"
                )
        
        4.  Put the ``core_profiles`` IDS in the new ``DBEntry``.
        5.  Print the ``core_profiles.ids_properties.version_put.data_dictionary``.
            What do you notice?

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/autoconvert_put.py


Exercise 4: Automatic conversion when loading IDSs
''''''''''''''''''''''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  For this exercise we will first create some test data:

            .. literalinclude:: imas_snippets/autoconvert_get.py
                :start-after: # 1.
                :end-before: # 2.
        
        2.  Reopen the ``DBEntry`` with the default DD version.
        3.  ``get`` the pulse schedule IDS. Print its
            ``version_put/data_dictionary`` and Data Dictionary version (with
            :py:meth:`~imas.util.get_data_dictionary_version`). What do you
            notice?
        4.  Use ``imas.util.print_tree`` to print all data in the loaded IDS. What do
            you notice?
        5.  Repeat steps 3 and 4, but set
            :py:param:`~imas.db_entry.DBEntry.get.autoconvert` to ``False``. What do
            you notice this time?

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/autoconvert_get.py


Use cases for disabling autoconvert
'''''''''''''''''''''''''''''''''''

As you could see in the exercise, disabling autoconvert enables you to retrieve all data
exactly as it was stored. This can be useful, especially for non-active IDSs which may
contain large changes between DD versions, such as:

-   Interactive plotting tools
-   Exploration of all stored data in a Data Entry
-   Etc.


.. caution::

    The :py:meth:`~imas.ids_convert.convert_ids` method warns you when data is not
    converted. Due to technical constraints, the ``autoconvert`` logic doesn't log any
    such warnings.

    You can work around this by explicitly converting the IDS:

    .. code-block:: python

        >>> # Continuing with the example from Exercise 4:
        >>> ps_noconvert = entry.get("pulse_schedule", autoconvert=False)
        >>> imas.convert_ids(ps_noconvert, "3.40.0")
        15:32:32 INFO     Parsing data dictionary version 3.40.0 @dd_zip.py:129
        15:32:32 INFO     Starting conversion of IDS pulse_schedule from version 3.25.0 to version 3.40.0. @ids_convert.py:350
        15:32:32 INFO     Element 'ec/antenna/phase' does not exist in the target IDS. Data is not copied. @ids_convert.py:396
        15:32:32 INFO     Element 'ec/antenna/launching_angle_pol/reference/data' does not exist in the target IDS. Data is not copied. @ids_convert.py:396
        15:32:32 INFO     Element 'ec/antenna/launching_angle_tor/reference/data' does not exist in the target IDS. Data is not copied. @ids_convert.py:396
        15:32:32 INFO     Conversion of IDS pulse_schedule finished. @ids_convert.py:366
        <IDSToplevel (IDS:pulse_schedule)>


.. _`Using custom builds of the Data Dictionary`:

Using custom builds of the Data Dictionary
------------------------------------------

In the previous sections we showed how you can direct imas-python to use a specific released
version of the Data Dictionary definitions. Sometimes it is useful to work with
unreleased (development or custom) versions of the data dictionaries as well.

.. caution::

    Unreleased versions of the Data Dictionary should only be used for testing.
    
    Do not use an unreleased Data Dictionary version for long-term storage: data
    might not be read properly in the future.

If you build the Data Dictionary, a file called ``IDSDef.xml`` is created. This file
contains all IDS definitions. To work with a custom DD build, you need to point imas-python
to this ``IDSDef.xml`` file:

.. code-block:: python
    :caption: Use a custom Data Dictionary build with imas-python

    my_idsdef_file = "path/to/IDSDef.xml"  # Replace with the actual path

    # Point IDSFactory to this path:
    my_factory = imas.IDSFactory(xml_path=my_idsdef_file)
    # Now you can create IDSs using your custom DD build:
    my_ids = my_factory.new("...")

    # If you need a DBEntry to put / get IDSs in the custom version:
    my_entry = imas.DBEntry("imas:hdf5?path=my-testdb", "w", xml_path=my_idsdef_file)


Once you have created the ``IDSFactory`` and/or ``DBEntry`` pointing to your custom DD
build, you can use them like you normally would.


.. rubric:: Footnotes

.. [#DDdefs] To be more precise, the Data Dictionary definitions are generated when the
    imas-python package is created. See :ref:`this reference <DD background>` for more
    details.
