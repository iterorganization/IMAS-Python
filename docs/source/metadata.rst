.. _`ids metadata`:

IDS metadata
============

Besides the data structure, the IMAS Data Dictionary also defines metadata
associated with elements in the IDS, such as coordinate information, units, etc.
imas-python provides the :py:class:`~imas.ids_metadata.IDSMetadata` API for
interacting with this metadata.

On this page you find several examples for querying and using the metadata of
IDS elements.

.. seealso::
    imas-python advanced training: :ref:`Using metadata`


Overview of available metadata
------------------------------

An overview of available metadata is given in the API documentation for
:py:class:`~imas.ids_metadata.IDSMetadata`.
The documented attributes are always available, but additional metadata from the data
dictionary may be available as well.
For example, the data dictionary indicates a ``lifecycle_last_change`` on all IDS
toplevels (in which DD version was that IDS last updated). This is not listed in the
metadata documentation, but you can still access it. See the following code sample:

.. code-block:: pycon

    >>> import imas
    >>> core_profiles = imas.IDSFactory().core_profiles()
    >>> core_profiles.metadata.lifecycle_last_change
    '3.39.0'


.. _`Using coordinates of quantities`:

Using coordinates of quantities
-------------------------------

All multi-dimensional quantities in an IDS have coordinate information. These
can be data nodes (for example 2D floating point data) or array of structure
nodes.


.. _`Get coordinate values`:

Get coordinate values
'''''''''''''''''''''

Each data node and array of structures has a ``coordinates`` attribute. By
indexing this attribute, you can retrieve the coordinate values for that
dimension. For example, ``coordinates[2]`` attempts to retrieve the coordinate
values for the third dimension of the data.

When another quantity in the IDS is used as a coordinate, that quantity is
looked up. See below example.

.. code-block:: python
    :caption: Example getting coordinate values belonging to a 1D quantity
    
    >>> core_profiles = imas.IDSFactory().core_profiles()
    >>> core_profiles.profiles_1d.resize(1)
    >>> profile = core_profiles.profiles_1d[0]
    >>> profile.grid.rho_tor_norm = [0, 0.15, 0.3, 0.45, 0.6]
    >>> # Electron temperature has rho_tor_norm as coordinate:
    >>> profile.electrons.temperature.coordinates[0]
    IDSNumericArray("/core_profiles/profiles_1d/1/grid/rho_tor_norm", array([0.  , 0.15, 0.3 , 0.45, 0.6 ]))

When a coordinate is just an index, imas-python generates a
:external:py:func:`numpy.arange` with the same length as the data. See below
example.

.. code-block:: python
    :caption: Example getting index coordinate values belonging to an array of structures

    >>> pf_active = imas.IDSFactory().pf_active()
    >>> pf_active.coil.resize(10)
    >>> # Coordinate1 of coil is an index 1...N
    >>> pf_active.coil.coordinates[0]
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

.. rubric:: Time coordinates

Time coordinates are a special case: the coordinates depend on whether the IDS
is in homogeneous time mode or not. imas-python handles this transparently.

.. code-block:: python
    :caption: Example getting time coordinate values

    >>> core_profiles = imas.IDSFactory().core_profiles()
    >>> # profiles_1d is a time-dependent array of structures:
    >>> core_profiles.profiles_1d.coordinates[0]
    [...]
    ValueError: Invalid IDS time mode: ids_properties/homogeneous_time is <IDSInt0D (IDS:core_profiles, ids_properties/homogeneous_time, empty INT_0D)>, was expecting 0 or 1.
    >>> core_profiles.ids_properties.homogeneous_time = \\
    ...     imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS
    >>> # In homogeneous time mode, the root /time array is used
    >>> core_profiles.time = [0, 1]
    >>> core_profiles.profiles_1d.resize(2)
    >>> core_profiles.profiles_1d.coordinates[0]
    IDSNumericArray("/core_profiles/time", array([0., 1.]))
    >>> # But in heterogeneous time mode, profiles_1d/time is used instead
    >>> core_profiles.ids_properties.homogeneous_time = \\
    ...     imas.ids_defs.IDS_TIME_MODE_HETEROGENEOUS
    >>> core_profiles.profiles_1d.coordinates[0]
    array([-9.e+40, -9.e+40])

.. rubric:: Alternative coordinates

Sometimes the Data Dictionary indicates that multiple other quantities could be
used as a coordinate. For example, the
``distribution(i1)/profiles_2d(itime)/density(:,:)`` quantity in the
``distributions`` IDS has as first coordinate
``distribution(i1)/profiles_2d(itime)/grid/r OR
distribution(i1)/profiles_2d(itime)/grid/rho_tor_norm``. This means that either
``r`` or ``rho_tor_norm`` can be used as coordinate. When requesting such a
coordinate from imas-python, four things may happen:

1.  When ``r`` is empty and ``rho_tor_norm`` not, ``coordinates[0]`` will return
    ``rho_tor_norm``.
2.  When ``rho_tor_norm`` is empty and ``r`` not, ``coordinates[0]`` will return
    ``r``.
3.  When both ``r`` and ``rho_tor_norm`` are not empty, imas-python raises an error
    because it cannot determine which of the two coordinates should be used.
4.  Similarly, an error is raised by imas-python when neither ``r`` nor
    ``rho_tor_norm`` are set.


.. seealso::
    API documentation for :py:class:`~imas.ids_coordinates.IDSCoordinates`


Query coordinate information
''''''''''''''''''''''''''''

In imas-python you can query coordinate information in two ways:

1.  Directly query the coordinate attribute on the metadata:
    :code:`<quantity>.metadata.coordinate2` gives you the coordinate information
    for the second dimension of the quantity.
2.  Use the :py:attr:`~imas.ids_metadata.IDSMetadata.coordinates` attribute:
    :code:`<quantity>.metadata.coordinates` is a tuple containing all coordinate
    information for the quantity.

The coordinate information from the Data Dictionary is parsed and stored in an
:py:class:`~imas.ids_coordinates.IDSCoordinate`. The Data Dictionary has
several types of coordinate information:

1.  When the coordinate is an index, the Data Dictionary indicates this via
    ``1...N``. When a literal ``N`` is given, no restrictions apply.
    
    It is also possible to have a specific value for ``N``, for example
    ``1...3``. Then, this dimension can contain at most 3 items.
2.  When another quantity in the IDS is used as a coordinate, the coordinate
    indicates the path to that other quantity.

.. TODO::
    Detailed coordinate descriptions should happen in the DD docs. Link to that
    when available.

.. code-block:: python
    :caption: Examples querying coordinate information

    >>> pf_active = imas.IDSFactory().pf_active()
    >>> # coordinate1 of pf_active/coil is an index (the number of the coil)
    >>> pf_active.coil.metadata.coordinate1
    IDSCoordinate('1...N')
    >>> pf_active.coil.resize(1)
    >>> # pf_active/coil/current_limit_max is 2D, so has two coordinates
    >>> # Both refer to another quantity in the IDS
    >>> pf_active.coil[0].current_limit_max.metadata.coordinates
    (IDSCoordinate('coil(i1)/b_field_max'), IDSCoordinate('coil(i1)/temperature'))


.. seealso::
    API documentation for :py:class:`~imas.ids_coordinates.IDSCoordinate`.


Query alternative coordinates
'''''''''''''''''''''''''''''

Starting in Data Dictionary 4.0, a coordinate quantity may indicate alternatives for
itself. These alternatives are stored in the metadata attribute
:py:attr:`~imas.ids_metadata.IDSMetadata.alternative_coordinates`.

For example, most quantities in ``profiles_1d`` of the ``core_profiles`` IDS have
``profiles_1d/grid/rho_tor_norm`` as coordinate. However, there are alternatives
that may be used instead (e.g. ``rho_tor``, ``psi``, ...). This is then indicated in
the metadata of ``rho_tor_norm``:

.. code-block:: python
    :caption: Showing alternative coordinates in Data Dictionary version 4.0.0

    >>> import imas
    >>> import rich
    >>> dd4 = imas.IDSFactory("4.0.0")
    >>> core_profiles = dd4.core_profiles()
    >>> rich.print(cp.profiles_1d[0].grid.rho_tor_norm.metadata.alternative_coordinates)
    (
        IDSPath('profiles_1d(itime)/grid/rho_tor'),
        IDSPath('profiles_1d(itime)/grid/psi'),
        IDSPath('profiles_1d(itime)/grid/volume'),
        IDSPath('profiles_1d(itime)/grid/area'),
        IDSPath('profiles_1d(itime)/grid/surface'),
        IDSPath('profiles_1d(itime)/grid/rho_pol_norm')
    )
