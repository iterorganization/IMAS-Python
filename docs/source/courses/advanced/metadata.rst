.. _`Using metadata`:

Using Data Dictionary metadata
==============================

imas-python provides convenient access to Data Dictionary metadata of any IDS node through
the ``metadata`` attribute:

.. code-block:: python

    >>> import imas
    >>> core_profiles = imas.IDSFactory().core_profiles()
    >>> core_profiles.metadata
    <IDSMetadata for 'core_profiles'>
    >>> core_profiles.time.metadata
    <IDSMetadata for 'time'>
    >>> # etc.

In this lesson we will show how to work with this metadata by exploring a couple of use
cases.


Overview of available metadata
------------------------------

The data dictionary metadata that is parsed by imas-python is listed in the API
documentation for :py:class:`~imas.ids_metadata.IDSMetadata`.

Note that not all metadata from the IMAS Data Dictionary is parsed by imas-python.
This metadata is still accessible on the :code:`metadata` attribute. You can use
:py:func:`imas.util.inspect` to get an overview of all metadata associated to an
element in an IDS.

.. code-block:: python
    :caption: Example showing all metadata for some ``core_profiles`` elements.

    >>> import imas
    >>> core_profiles = imas.IDSFactory().core_profiles()
    >>> imas.util.inspect(core_profiles.metadata)
    ╭---- <class 'imas.ids_metadata.IDSMetadata'> -----╮
    │ Container for IDS Metadata                         │
    │                                                    │
    │ ╭------------------------------------------------╮ │
    │ │ <IDSMetadata for 'core_profiles'>              │ │
    │ ╰------------------------------------------------╯ │
    │                                                    │
    │   alternative_coordinates = ()                     │
    │               coordinates = ()                     │
    │       coordinates_same_as = ()                     │
    │                 data_type = None                   │
    │             documentation = 'Core plasma profiles' │
    │     lifecycle_last_change = '3.39.0'               │
    │          lifecycle_status = 'active'               │
    │         lifecycle_version = '3.1.0'                │
    │                  maxoccur = 15                     │
    │                      name = 'core_profiles'        │
    │                      ndim = 0                      │
    │                      path = IDSPath('')            │
    │                  path_doc = ''                     │
    │               path_string = ''                     │
    │ specific_validation_rules = 'yes'                  │
    │              timebasepath = ''                     │
    │                      type = <IDSType.NONE: None>   │
    │                     units = ''                     │
    ╰----------------------------------------------------╯
    >>> imas.util.inspect(core_profiles.time.metadata)
    ╭------ <class 'imas.ids_metadata.IDSMetadata'> -------╮
    │ Container for IDS Metadata                             │
    │                                                        │
    │ ╭----------------------------------------------------╮ │
    │ │ <IDSMetadata for 'time'>                           │ │
    │ ╰----------------------------------------------------╯ │
    │                                                        │
    │ alternative_coordinates = ()                           │
    │             coordinate1 = IDSCoordinate('1...N')       │
    │             coordinates = (IDSCoordinate('1...N'),)    │
    │     coordinates_same_as = (IDSCoordinate(''),)         │
    │               data_type = <IDSDataType.FLT: 'FLT'>     │
    │           documentation = 'Generic time'               │
    │                maxoccur = None                         │
    │                    name = 'time'                       │
    │                    ndim = 1                            │
    │                    path = IDSPath('time')              │
    │                path_doc = 'time(:)'                    │
    │             path_string = 'time'                       │
    │            timebasepath = 'time'                       │
    │                    type = <IDSType.DYNAMIC: 'dynamic'> │
    │                   units = 's'                          │
    ╰--------------------------------------------------------╯


Coordinate metadata
-------------------

The Data Dictionary has coordinate information on all non-scalar nodes: arrays of
structures and data nodes that are not 0D. These coordinate descriptions can become
quite complicated, but summarized they come in two categories:

1.  Coordinates are indices.

    This is indicated by the Data Dictionary as coordinate = ``1...{x}``. Here ``{x}``
    can be a number (e.g. ``1...3``), which means that this dimension should have
    exactly ``x`` elements. ``{x}`` can also be a literal ``N``: ``1...N``, meaning that
    the size of this dimension does not have a predetermined size.

    Sometimes multiple variables have index variables, but they are still
    linked. For example, image sensors could have one variable indicating raw observed
    values per pixel, and another variable storing some processed quantities per pixel.
    In this case, the coordinates are indices (line / column index of the pixel), but
    these must be the same for both quantities. This information is stored in the
    :py:attr:`~imas.ids_metadata.IDSMetadata.coordinates_same_as` metadata.

2.  Coordinates are other quantities in the Data Dictionary.

    This is indicated by the Data Dictionary by specifying the path to the coordinate.
    There are multiple scenarios here, which are described in more detail in the section
    :ref:`Using coordinates of quantities`.

For most use cases it is not necessary to become an expert in all
intricacies of Data Dictionary coordinates. Instead, you can use the ``coordinates``
attribute of array of structures and data nodes. For example ``<ids
node>.coordinates[0]`` will give you the data to use for the first coordinate.


Exercise 1: Using coordinates
'''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``core_profiles`` IDS. You can refresh how to
            do this in the following section of the basic training material: :ref:`Open
            an IMAS database entry`.

            a.  Print the coordinate of ``profiles_1d[0].electrons.temperature``. This
                is a 1D array, so there is only one coordinate. It can be accessed with
                ``<node>.coordinates[0]``. Do you recognize the coordinate?
            b.  Print the coordinate of the ``profiles_1d`` array of structures. What
                do you notice?
            c.  Change the time mode of the IDS from homogeneous time to heterogeneous
                time. You do this by setting 
                ``ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_HETEROGENEOUS``.
                Print the coordinate of the ``profiles_1d`` array of structure again.
                What has changed?

        2.  Load the training data for the ``equilibrium`` IDS.

            a.  What is the coordinate of ``time_slice[0]/profiles_2d``?
            b.  What are the coordinates of ``time_slice[0]/profiles_2d[0]/b_field_r``?

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/coordinates.py


Exercise 2: Alternative coordinates
'''''''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Create an empty ``distributions`` IDS.
        2.  Use the ``metadata`` attribute to find the coordinates of
            ``distribution[]/profiles_2d[]/density``. What do you notice?

            .. hint::
                :collapsible:

                ``distribution`` and ``profiles_2d`` are arrays of structures. When
                creating an empty IDS, these arrays of structures are empty as well.

                To access the metadata of the structures inside, you have two options:

                1.  Resize the array of structures so you can access the metadata of the
                    elements.
                2.  Use the indexing operator on
                    :py:class:`~imas.ids_metadata.IDSMetadata`. For example,
                    ``distributions.metadata["distribution/wave"]`` to get the metadata
                    of the ``distribution[]/wave`` array of structures.
        3.  Resize the ``distribution`` and ``distribution[0].profiles_2d`` arrays of
            structures. Retrieve the coordinate values through the
            ``distribution[0].profiles_2d[0].density.coordinates`` attribute. What do
            you notice?
        4.  You can still use the metadata to go to the coordinate node options:

            a.  Use the :py:attr:`~imas.ids_coordinates.IDSCoordinate.references`
                attribute of the :py:class:`~imas.ids_coordinates.IDSCoordinate`
                objects in the ``metadata`` to get the paths to each of the coordinate
                options. This will give you the :py:class:`~imas.ids_path.IDSPath`
                objects for each coordinate option.
            b.  Then, use :py:meth:`IDSPath.goto <imas.ids_path.IDSPath.goto>` to go
                to the corresponding IDS node.

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/alternative_coordinates.py


Units and dimensional analysis with Pint
----------------------------------------

.. note::

    This section uses the python package `Pint` to perform calculations with units. This
    package can be installed by following `the instructions on their website
    <https://pint.readthedocs.io/en/stable/getting/index.html>`_.

The Data Dictionary specifies the units of stored quantities. This metadata is
accessible in imas-python via :py:attr:`metadata.units
<imas.ids_metadata.IDSMetadata.units>`. In most cases, these units are in a format
that ``pint`` can understand (for example ``T``, ``Wb``, ``m^-3``, ``m.s^-1``).

There are some exceptions to that, with the main ones ``-`` (indicating a quantity is
dimensionless), ``Atomic Mass Unit`` and ``Elementary Charge Unit``. There are also
cases when units are dependent on the context that a quantity is used, but we will not
go into that in this lesson.

For conversion of units from the Data Dictionary format to pint units, we recommend
creating a custom function, such as the following:

.. literalinclude:: imas_snippets/calc_with_units.py
    :caption: Convert DD units to Pint Units
    :start-at: # Create pint UnitRegistry
    :end-before: # End


Exercise 3: Calculate the mass density from ``core_profiles/profiles_1d``
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``core_profiles`` IDS.
        2.  Select the first time slice of ``profiles_1d`` for the calculation.
        3.  Create a ``pint.UnitRegistry`` and conversion function from DD units to pint
            units.
        4.  Calculate the mass density:

            a.  Create the result variable with the correct unit (``kg.m^-3``):
                ``mass_density = ureg("0 kg.m^-3")``.
            b.  Loop over all ion and neutral species in profiles_1d. For each one,
                calculate the mass of the species (the sum of the masses of the elements
                that comprise the species) and multiply it with the species density to
                get the mass density of the species.

                Use the ``metadata.units`` and ``dd_to_pint`` conversion function to get
                the correct units during the calculation.
            c.  Print the total mass density (the sum of all species mass densities) in
                SI units (``kg.m^-3``).

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/calc_with_units.py
