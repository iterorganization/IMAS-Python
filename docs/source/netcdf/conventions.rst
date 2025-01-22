.. _`IMAS conventions for the netCDF data format`:

===========================================
IMAS conventions for the netCDF data format
===========================================

This page describes the conventions for storing `IMAS
<https://imas.iter.org/>`__ data in the netCDF4 data format. These conventions
build on top of the conventions described in the `NetCDF User Guide (NUG)
<https://docs.unidata.ucar.edu/nug/current/index.html>`__ and borrow as much as
possible from the `Climate and Forecast (CF) conventions
<https://cfconventions.org/>`__.


Introduction
============

Goals
-----

The netCDF library is a cross-platform library that enables to read and write
*self-describing* datasets consisting of multi-dimensional arrays. The purpose
of these IMAS conventions is to define how to store IMAS data, conforming to the
`IMAS Data Dictionary <https://confluence.iter.org/display/IMP/Data+Model>`__,
in a netCDF file.


Principles for design
---------------------

The following principles are followed in the design of these conventions:

1.  The data model described by the IMAS Data Dictionary is leading.
2.  The data should be self-describing without needing to access the Data
    Dictionary documentation. All relevant metadata should be available in the
    netCDF file.
3.  Widely used conventions, like the Climate and Forecast conventions, should
    be used as much as possible.
4.  It should be possible to store any valid IDS (according to the Data
    Dictionary) in an IMAS netCDF file. 


Terminology
-----------

The terms in this document that refer to components of a netCDF file are defined
in the NetCDF User's Guide (NUG) and/or the CF Conventions. Some of those
definitions are repeated below for convenience.

.. glossary::

    auxiliary coordinate variable
        Any netCDF variable that contains coordinate data, but is not a
        coordinate variable (in the sense of that term defined by the NUG and
        used by this standard -- see below). Unlike coordinate variables, there
        is no relationship between the name of an auxiliary coordinate variable
        and the name(s) of its dimension(s).

        .. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#terminology

    coordinate variable
        We use this term precisely as it is defined in the `NUG section on
        coordinate variables
        <https://docs.unidata.ucar.edu/nug/current/best_practices.html#bp_Coordinate-Systems>`__.
        It is a one-dimensional variable with the same name as its dimension
        [e.g., ``time(time)``], and it is defined as a numeric data type with
        values in strict monotonic order (all values are different, and they are
        arranged in either consistently increasing or consistently decreasing
        order). Missing values are not allowed in coordinate variables.

        .. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#terminology

    multi-dimensional coordinate variable
        An :term:`auxiliary coordinate variable` that is multidimensional.

        .. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#terminology


    time dimension
        A dimension of a netCDF variable that has an associated time coordinate variable.

        .. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#terminology


NetCDF files and components
===========================

In this section we describe conventions associated with filenames and the basic
components of a netCDF file.


Filename
--------

NetCDF files should have the file name extension "``.nc``".


File format
-----------

These conventions require functionality that is only available in the netCDF-4
file format. As a result, this is the only supported file format for IMAS netCDF
files.


.. _`global attributes`:

Global attributes
-----------------

The following global (file-level) attributes should be set in IMAS netCDF files:

``Conventions``
    The ``Conventions`` attribute is set to "``IMAS``" to indicate that the file
    follows these IMAS conventions.

``data_dictionary_version``
    The ``data_dictionary_version`` attribute is set to the version string of
    the Data Dictionary it follows. For example: "``3.38.1``", "``3.41.0``".


Groups
------

The IMAS Data Dictionary organizes data in Interface Data Structures (IDS). The
IMAS Access Layer stores collections of IDSs in a Data Entry. Multiple
*occurrences* of an IDS can occur in a Data Entry.

This same structure is mirrored in IMAS netCDF files, using netCDF groups. All
data inside an IDS structure is stored as variables in the netCDF group "``{IDS
name}/{occurrence}/``". ``IDS name`` represents the name of the IDS, such as
``core_profiles``, ``pf_active``, etc. ``occurrence`` is an integer ``>= 0``
indicating the occurrence number of the IDS. When only one occurrence of the IDS
is stored in the netCDF file, the occurrence is typically ``0``.

.. code-block:: text
    :caption: Example group structure for an IDS

    /core_profiles/0
    /pf_active/0
    /pf_active/1
    /summary/0

Each IDS/occurrence is stored independently. There are no shared variables or
dimensions.


Variables
---------

Variable names
''''''''''''''

NetCDF variable names are derived from the Data Dictionary node names by taking
their path and replacing the forward slashes (``/``) by periods (``.``). For
example, the netCDF variable name for ``profiles_1d/ion/temperature`` in the
``core_profiles`` IDS is ``profiles_1d.ion.temperature``.


Data Types
''''''''''

Data types of variables are defined by the IMAS Data Dictionary:

- ``STR_*``: strings are represented in the netCDF file with the ``string`` data
  type.
- ``INT_*``: integer numbers are represented in the netCDF file with the ``int``
  (32-bits signed integer) data type.
- ``FLT_*``: floating point numbers are represented in the netCDF file with the
  ``double`` (64-bits floating point) data type.
- ``CPX_*``: complex numbers are represented in the netCDF file using a compound
  data type with an ``r`` (for the real-valued) and ``i`` (for the
  imaginary-valued) component. See the `nc-complex
  <https://nc-complex.readthedocs.io/en/latest/>`__ package for further details.

The IMAS Data Dictionary also defines Structures and Arrays of Structures. They
don't contain data themselves, but can be stored as variables in the netCDF file
to attach metadata (such as documentation) to.


Variable attributes
'''''''''''''''''''

The following attributes can be present on the netCDF variables:

``_FillValue``
    The ``_FillValue`` attribute specifies the fill value used to pre-fill disk
    space allocated to the variable.

    It is recommended to use the default netCDF fill values: ``-2,147,483,647``
    for integers, ``9.969209968386869e+36`` for floating point data and the
    empty string ``""`` for string data.

    .. seealso:: https://docs.unidata.ucar.edu/netcdf-c/current/attribute_conventions.html

``ancillary_variables``
    The IMAS Data Dictionary allows error bar nodes (ending in ``_error_upper``,
    ``_error_lower``) for many quantities. When these error nodes are filled, it
    is recommended to fill the ``ancillary_variables`` attribute with a blank
    separated list [#blank_separated]_ of the names of the error bar variables.

    .. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#ancillary-data

``coordinates``
    The ``coordinates`` attribute contains a blank separated list
    [#blank_separated]_ of the names of auxiliary coordinate variables. There
    is no restriction on the order in which the auxiliary variables appear.

    See the :ref:`Dimensions and auxiliary coordinates` section on how to
    determine auxiliary coordinates from the Data Model defined by the IMAS Data
    Dictionary.

    .. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#coordinate-system

``documentation``
    The ``documentation`` attribute contains a documentation string for the
    variable. This documentation should correspond to the documentation string
    defined by the IMAS Data Dictionary.

``sparse``
    When the ``sparse`` attribute is present, it indicates that the data in this
    variable does not span the full size of its dimensions. The value of this
    attribute should be a human-readable string indicating that not all values
    are filled.

    See the :ref:`Tensorization` section for more information and examples for
    the ``sparse`` attribute and handling data that does not span the full size
    of its dimensions.

``units``
    A string indicating the units used for the variable's data. *Units* are
    defined by the IMAS Data Dictionary and applications must follow this.

    .. note::

        The IMAS Data Dictionary units currently don't always adhere to the
        `UDUNITS <https://docs.unidata.ucar.edu/udunits/current/>`__ conventions.
        Tracker `IMAS-5246 <https://jira.iter.org/browse/IMAS-5246>`__ was
        created for this.

    .. seealso:: https://docs.unidata.ucar.edu/netcdf-c/current/attribute_conventions.html


.. [#blank_separated] Several string attributes are defined by this standard to
    contain "blank-separated lists". Consecutive words in such a list are
    separated by one or more adjacent spaces. The list may begin and end with
    any number of spaces.


IDS metadata and provenance
===========================

The Data Dictionary describes an ``ids_properties`` structure in every IDS,
which contains IDS metadata and provenance. See, for example, the :ref:`time
dimensions` section where the ``ids_properties.homogeneous_time`` metadata is
used.

IMAS netCDF writers are recommended to overwrite the following metadata:

- ``ids_properties.version_put.data_dictionary``: fill with the Data Dictionary
  version used for this IDS. This must match the ``data_dictionary_version``
  :ref:`global attribute <global attributes>`.
- ``ids_properties.version_put.access_layer``: fill with ``"N/A"``, since this
  IDS is not written by the IMAS Access Layer.
- ``ids_properties.version_put.access_layer_language``: fill with the name and
  version of the netCDF writer, for example ``imas-python 1.1.0``.

All other IDS metadata and provenance should be filled by the user or software
that provides the IDS data.


.. _`Dimensions and auxiliary coordinates`:

Dimensions and auxiliary coordinates
====================================

NetCDF dimensions and :term:`auxiliary coordinate variable`\ s are derived from
the coordinate metadata stored in the IMAS Data Dictionary.

.. list-table::
    :header-rows: 1
    
    - * Data Dictionary Coordinate
      * Interpretation
      * NetCDF implications
    - * ``1...N``
      * There is no coordinate for this node, there is no limit on size.
      * Independent dimension.
    - * ``1...i``, with ``i=1,2,3,...``
      * There is no coordinate for this node, size must be exactly ``i`` or 0.
      * Independent dimension.
    - * ``1...N`` (same as ``x/y/z``)
      * There is no coordinate, but this node must have the same size as node ``x/y/z``.
      * Shared dimension with variable ``x.y.z``, ``x.y.z`` is **not** an auxiliary coordinate.
    - * ``x/y/z``
      * Node ``x/y/z`` is the coordinate for this node.
      * Shared dimension with variable ``x.y.z``, ``x.y.z`` can be an auxiliary coordinate.
    - * ``u/v/w OR x/y/z``
      * Either node ``u/v/w`` or node ``x/y/z`` must be filled and it is the coordinate for this node.
      * Shared dimension with variables ``u.v.w`` and ``x.y.z``. Both ``u.v.w`` and ``x.y.z`` can be auxiliary coordinates.
    - * ``x/y/z OR 1...1``
      * Either node ``x/y/z`` is the coordinate for this node, or this node must have size 1.
      * Shared dimension with variable ``x.y.z`` [#or1]_, ``x.y.z`` can be an auxiliary coordinate.
    - * ``1...N`` (same as ``x/y/z OR 1...1``)
      * There is no coordinate for this node, but this node must either have the same size as node ``x/y/z`` or have size 1.
      * Shared dimension with variable ``x.y.z`` [#or1]_, ``x.y.z`` is **not** an auxiliary coordinate.

.. [#or1] Even though a dummy, size=1, dimension could be used if the data
    stored in the node is never exceeding 1 element, this decision was made to
    allow determining dimension names without having to inspect the data stored.


.. _`Time dimensions`:

Time dimensions
---------------

The IMAS Data Dictionary provides for three different time modes. The special
integer variable ``ids_properties.homogeneous_time`` indicates which of the time
mode an IDS is using:

- Heterogeneous time mode (``ids_properties.homogeneous_time = 0``), multiple
  time dimensions may exist in the IDS.
- Homogeneous time mode (``ids_properties.homogeneous_time = 1``), there is only
  a single time coordinate, which is stored in the ``time`` :term:`coordinate
  variable`.
- Time independent mode (``ids_properties.homogeneous_time = 2``) means that
  there is no time-varying data in this IDS and only variables that don't have a
  time dimension may be stored.

The selected time mode impacts which :term:`time dimension` is used, see below
table for some examples.

.. list-table::
    :header-rows: 1

    * - Example Data Dictionary node
      - Data Dictionary time coordinate
      - Time dimension (heterogeneous mode)
      - Time dimension (homogeneous mode)
    * - ``global_quantities/ip`` (``core_profiles`` IDS)
      - ``time``
      - ``time``
      - ``time``
    * - ``coil/current/data`` (``pf_active`` IDS)
      - ``coil(i1)/current/time``
      - ``coil.current.time``
      - ``time``
    * - ``time_slice`` (``equilibrium`` IDS) [#aos]_
      - ``time_slice(itime)/time``
      - ``time_slice.time``
      - ``time``

.. [#aos] This is an Array of Structures and not a data variable. See the
    :ref:`Tensorization` section for more information on Arrays of Structures.


Additional auxiliary coordinates
--------------------------------

Additional auxiliary coordinates may be attached to data variables, to indicate
labels and/or alternative coordinates.

Some examples where this is useful:

-   Plasma composition array of structures have names (DDv4) / labels (DDv3),
    for example ``profiles_1d.ion.label`` in the ``core_profiles`` IDS. This
    variable may be an auxiliary coordinate to variables like
    ``profiles_1d.ion.temperature``.
-   Other indexed Arrays of Structures in the Data Dictionary may have ``name``
    and/or ``identifier``, such as ``coil`` in the ``pf_active`` IDS. These may
    be auxiliary coordinates to variables defined for these coils, like
    ``coil.resistance``.

.. seealso:: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#_labels_and_alternative_coordinates


.. _`Tensorization`:

Tensorization
=============

The Data Model described by the IMAS Data Dictionary is a tree structure
containing many *structures*, *arrays of structures* and data nodes. To fit that
in the netCDF data model as described in this document, we need to *tensorize*
the tree structure. This section explains that process in detail.

Tensorizing the data effectively converts all *arrays of structures* to one
structure of tensorized arrays. For some (abstract) data nodes, this means:

.. code-block:: text

    aos[i].data[j, k]       =>  aos.data[i, j, k]
    aos[i].aos[j].data[k]   =>  aos.data[i, j, k]
    aos[i].struct.data[j]   =>  aos.struct.data[i, j]

    # Tensorization doesn't affect data nodes outside arrays of structures
    struct.data[i, j]       =>  struct.data[i, j]

We will first walk through the tensorization process by looking at the
``profiles_1d(itime)/j_tor`` variable in the ``core_profiles`` IDS. This is a
data variable called ``j_tor`` inside the ``profiles_1d`` *array of structures*.
As the name implies, ``profiles_1d`` is an array containing structures. These
structures can have many child nodes (as we will see), but we will focus on the
``j_tor`` data node.


Tensorization example
---------------------

The following table summarizes the main Data Dictionary metadata for
``profiles_1d/j_tor`` and the other relevant nodes of the ``core_profiles`` IDS:

.. csv-table::
    :header: , Node type, Coordinates

    ``profiles_1d/j_tor``, ``FLT_1D``, 1: ``profiles_1d/grid/rho_tor_norm``
    ``profiles_1d/grid``, Structure, 
    ``profiles_1d/grid/rho_tor_norm``, ``FLT_1D``, 1: ``1...N``
    ``profiles_1d``, Array of Structures, 1: ``profiles_1d/time``
    ``profiles_1d/time``, ``FLT_0D``,
    ``time``, ``FLT_1D``, 1: ``1...N``

Let's go through this table:

1.  The ``j_tor`` data node is a 1-dimensional array of floating point numbers.
    Its coordinate is another data node (``rho_tor_norm``) inside the sibling
    structure ``profiles_1d/grid``.
2.  The ``profiles_1d/grid`` node is a structure in the data dictionary. It is
    0-dimensional and has no coordinates. It has several child nodes, among
    which ``rho_tor_norm``.
3.  The ``profiles_1d/grid/rho_tor_norm`` data node is also a 1-dimensional
    array of floating point numbers. Its coordinate is an index without a fixed
    size, as indicated by ``1...N``.
4.  Moving up in the data tree, we have the 1-dimensional array of structures
    ``profiles_1d``. It has a time dimension: its coordinate is
    ``profiles_1d/time``. :ref:`Time dimensions` are special in the Data Model
    (see the link for more details): when using *heterogeneous time mode* we
    need to use the ``profiles_1d/time`` nodes as coordinate, while in
    *homogeneous time mode* we use the root ``time`` node.
5.  The ``profiles_1d/time`` data node is a 0-dimensional (scalar) floating
    point number. Note that there is 1 such node per instance of the
    ``profiles_1d`` array of structures.
6.  The ``time`` data node is another 1-dimensional floating point number. Its
    coordinate is an index without a fixed size, as indicated by ``1...N``.


.. code-block:: javascript
    :caption: Dummy data for ``profiles_1d/j_tor`` in `JSON <https://en.wikipedia.org/wiki/JSON>`__ notation, using *heterogeneous time mode*
    :name: j_tor-dummy-data

    {
      "profiles_1d": [
        {
          "grid": {
            "rho_tor_norm": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
          },
          "j_tor": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
          "time": 0.0
        },
        {
          "grid": {
            "rho_tor_norm": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
          },
          "j_tor": [2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
          "time": 0.1
        },
        {
          "grid": {
            "rho_tor_norm": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
          },
          "j_tor": [3.0, 3.1, 3.2, 3.3, 3.4, 3.5],
          "time": 0.2
        }
      ]
    }


Tensorizing the data effectively converts all *arrays of structures* to one
structure of tensorized arrays. For our ``j_tor`` data node this means:

.. code-block:: text

    profiles_1d[i].j_tor[j]  =>  profiles_1d.j_tor[i, j]

After tensorization ``profiles_1d.j_tor`` is a 2-dimensional array! This means
there are two netCDF dimensions for ``j_tor``. The first is the :ref:`time
dimension <Time dimensions>` coming from the ``profiles_1d`` array of
structures. The second dimension is the dimension with the
``profiles_1d/grid/rho_tor_norm`` coordinate.

Let's summarize tensorization for all data nodes related to ``j_tor``:

.. csv-table::
    :header: NetCDF variable, NetCDF dimensions (*homogeneous/heterogeneous time mode*)

    ``profiles_1d.j_tor``, "(``time``/``profiles_1d.time``, ``profiles_1d.grid.rho_tor_norm:i``\ [#dimsuffix]_)"
    ``profiles_1d.grid`` [#docnode]_ , ()
    ``profiles_1d.grid.rho_tor_norm``, "(``time``/``profiles_1d.time``, ``profiles_1d.grid.rho_tor_norm:i``\ [#dimsuffix]_)"
    ``profiles_1d`` [#docnode]_ , ()
    ``profiles_1d.time``, (``profiles_1d.time``)
    ``time``, (``time``)

.. [#dimsuffix] We add the ``:i`` suffix to the dimension name, because the
    netCDF variable ``profiles_1d.grid.rho_tor_norm`` is a 2D array after
    tensorization. Therefore it cannot be a Coordinate as defined in the `NetCDF
    User Guide (NUG)
    <https://docs.unidata.ucar.edu/nug/current/best_practices.html#bp_Coordinate-Systems>`__
    and the dimension name should not be the same as the variable name.

.. [#docnode] Structures and Arrays of structures are included in the netCDF
    file to store metadata (such as documentation), but they don't contain data
    and are therefore dimensionless.


.. csv-table::
    :header: NetCDF variable, Auxiliary coordinates (*homogeneous/heterogeneous time mode*)

    ``profiles_1d.j_tor``, "``time profiles_1d.grid.rho_tor_norm`` /

    ``profiles_1d.time profiles_1d.grid.rho_tor_norm``"
    ``profiles_1d.grid.rho_tor_norm``, ``time`` / ``profiles_1d.time``
    ``profiles_1d.time``, \-
    ``time``, \-


.. code-block:: javascript
    :caption: Tensorizing the :ref:`dummy data <j_tor-dummy-data>` of ``j_tor``

    {
      "profiles_1d": null,
      "profiles_1d.grid": null,
      "profiles_1d.grid.rho_tor_norm": [
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
      ],
      "profiles_1d.j_tor": [
        [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
        [2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
        [3.0, 3.1, 3.2, 3.3, 3.4, 3.5],
      ],
      "time": [0.0, 0.1, 0.2]
    }


Tensorizing data with varying shapes
------------------------------------

In the example in the previous section, the data shapes were identical for each
array of structures. After tensorization this data became nicely
hyper-rectangular. However, the IMAS Data Model allows differently shaped data
across arrays of structures that doesn't tensorize so nicely.

In this section we have a look at two such scenerios:

1.  Varying sizes of data inside arrays of structures.
2.  Varying sizes of nested arrays of structures.


Varying sizes of data inside arrays of structures
'''''''''''''''''''''''''''''''''''''''''''''''''

Let's extend the example from the previous section. This time, the grid
``grid.rho_tor_norm`` is not constant in time. This can, for example, originate
from a grid refinement at ``time=0.2`` in the simulation:

.. code-block:: javascript
    :caption: Dummy ``core_profiles`` data with varying data sizes inside an *array of structures*

    {
      "profiles_1d": [
        {
          "grid": {
            "rho_tor_norm": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
          },
          "j_tor": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
          "time": 0.0
        },
        {
          "grid": {
            "rho_tor_norm": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
          },
          "j_tor": [2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
          "time": 0.1
        },
        {
          "grid": {
            "rho_tor_norm": [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
          },
          "j_tor": [3.0, 3.1, 3.2, 3.25, 3.3, 3.35, 3.4, 3.5],
          "time": 0.2
        }
      ]
    }

When we tensorize this data, we end up with missing values (indicated with
``null``) in the tensorized arrays. These missing values will be stored in the
netCDF file by the default netCDF ``_FillValue``.

.. code-block:: javascript

    {
      "profiles_1d": null,
      "profiles_1d.grid": null,
      "profiles_1d.grid.rho_tor_norm": [
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, null, null],
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, null, null],
        [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
      ],
      "profiles_1d.grid.rho_tor_norm:shape": [[6], [6], [8]],
      "profiles_1d.j_tor": [
        [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, null, null],
        [2.0, 2.1, 2.2, 2.3, 2.4, 2.5, null, null],
        [3.0, 3.1, 3.2, 3.25, 3.3, 3.35, 3.4, 3.5],
      ],
      "profiles_1d.j_tor:shape": [[6], [6], [8]],
      "time": [0.0, 0.1, 0.2]
    }

What you can also see is that we have two additional variables:
``profiles_1d.grid.rho_tor_norm:shape`` and ``profiles_1d.j_tor:shape``. These
shape arrays indicate the original shape of the variables before tensorization.

The variables ``profiles_1d.grid.rho_tor_norm`` and ``profiles_1d.j_tor`` will
also have an additional attribute (``sparse``) indicating that it has missing
data and a ``:shape`` array with the pre-tensorized data shapes.


Varying sizes of nested arrays of structures
''''''''''''''''''''''''''''''''''''''''''''

Let's have a look at the following data structure. This describes a plasma
composed of two ion species: hydrogen and helium. One ionization state of
hydrogen is described, and two ionization states of helium.


.. code-block:: javascript
    :caption: Dummy ``core_profiles`` data with varying *array of structures* sizes

    {
      "profiles_1d": [
        "grid": {
          "rho_tor_norm": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        },
        "ion": [
          {
            "label": "H",
            "state": [
              {
                "label": "H+",
                "z_min": 1.0,
                "z_max": 1.0,
                "temperature": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
              }
            ]
          },
          {
            "label": "He",
            "state": [
              {
                "label": "He+",
                "z_min": 1.0,
                "z_max": 1.0,
                "temperature": [2.0, 2.1, 2.2, 2.3, 2.4, 2.5]
              },
              {
                "label": "He+2",
                "z_min": 2.0,
                "z_max": 2.0,
                "temperature": [3.0, 3.1, 3.2, 3.3, 3.4, 3.5]
              }
            ]
          }
        ]
      ]
    }

When we tensorize this data, we end up with the following. ``null`` is used to
indicate missing data. Note that the ``profiles_1d`` array of structure is still
tensorized, even though there is only a single element:

.. code-block:: javascript

  {
    "profiles_1d": null,
    "profiles_1d.grid": null,
    "profiles_1d.grid.rho_tor_norm": [[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]]
    "profiles_1d.ion": null,
    "profiles_1d.ion.label": [["H", "He"]],
    "profiles_1d.ion.state": null,
    "profiles_1d.ion.state:shape": [[[1], [2]]],
    "profiles_1d.ion.state.label": [[
      ["H+", null],
      ["He+", "He+2"]
    ]],
    "profiles_1d.ion.state.z_min": [[
      [1.0, null],
      [1.0, 2.0]
    ]],
    "profiles_1d.ion.state.z_max": [[
      [1.0, null],
      [1.0, 2.0]
    ]],
    "profiles_1d.ion.state.temperature": [[
      [
        [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
        [null, null, null, null, null, null]
      ],
      [
        [2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
        [3.0, 3.1, 3.2, 3.3, 3.4, 3.5]
      ]
    ]],
    "profiles_1d.ion.state.temperature:shape": [[[6], [0], [6], [6]]]
  }

Again we see the ``:shape`` arrays, but now there's also a ``:shape`` array for
the ``profiles_1d.ion.state`` array of structures.
