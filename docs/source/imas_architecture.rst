imas-python architecture
========================

This document provides a brief overview of the components of imas-python, grouped into
different functional areas.

We don't aim to give detailed explanations of the code or the algorithms in it. These
should be annotated in more detail in docstrings and inline comments.


Data Dictionary metadata
------------------------

These classes are used to parse and represent IDS metadata from the Data Dictionary.
Metadata objects are generated from a Data Dictionary XML and are (supposed to be)
immutable.

-   :py:mod:`imas.ids_metadata` contains the main metadata class
    :py:class:`~imas.ids_metadata.IDSMetadata`. This class is generated from an
    ``<IDS>`` or ``<field>`` element in the Data Dictionary XML and contains all
    (parsed) data belonging to that ``<IDS>`` or ``<field>``. Most of the (Python)
    attributes correspond directly to an attribute of the XML element.

    This module also contains the :py:class:`~imas.ids_metadata.IDSType` enum. This
    enum corresponds to the Data Dictionary notion of ``type`` which can be ``dynamic``,
    ``constant``, ``static`` or unavailable on a Data Dictionary element.

-   :py:mod:`imas.ids_coordinates` contains two classes:
    :py:class:`~imas.ids_coordinates.IDSCoordinate`, which handles the parsing of
    coordinate identifiers from the Data Dictionary, and
    :py:class:`~imas.ids_coordinates.IDSCoordinates`, which handles coordinate
    retrieval and validation of IDS nodes.

    :py:class:`~imas.ids_coordinates.IDSCoordinate`\ s are created for each coordinate
    attribute of a Data Dictionary element: ``coordinate1``, ``coordinate2``, ...
    ``coordinate1_same_as``, etc.

    :py:class:`~imas.ids_coordinates.IDSCoordinates` is created and assigned as
    ``coordinates`` attribute of :py:class:`~imas.ids_struct_array.IDSStructArray` and
    :py:class:`~imas.ids_primitive.IDSPrimitive` objects. This class is responsible
    for retrieving coordinate values and for checking the coordinate consistency in
    :py:func:`~imas.ids_toplevel.IDSToplevel.validate`.

-   :py:mod:`imas.ids_data_type` handles parsing Data Dictionary ``data_type``
    attributes (see method :py:meth:`~imas.ids_data_type.IDSDataType.parse`) to an
    :py:class:`~imas.ids_data_type.IDSDataType` and number of dimensions.

    :py:class:`~imas.ids_data_type.IDSDataType` also has attributes for default values
    and mappings to Python / Numpy / Access Layer type identifiers.

-   :py:mod:`imas.ids_path` handles parsing of IDS paths to
    :py:class:`~imas.ids_path.IDSPath` objects. Paths can occur as the ``path``
    attribute of Data Dictionary elements, and inside coordinate identifiers.

    .. caution::

        Although an :py:class:`~imas.ids_path.IDSPath` in imas-python implements roughly
        the same concept as `the "IDS Path syntax" in the Data Dictionary
        <https://github.com/iterorganization/imas-data-dictionary/blob/develop/html_documentation/utilities/IDS-path-syntax.md>`__,
        they are not necessarily the same thing!

        At the moment of writing this (January 2024), the IDS path definition in the
        Data Dictionary is not yet finalized.
        Be aware that the syntax of imas-python's :py:class:`~imas.ids_path.IDSPath` may
        differ slightly and might be incompatible with the definition from the Data
        Dictionary.


Data Dictionary building and loading
------------------------------------

The following submodules are responsible for building the Data Dictionary and loading DD
definitions at runtime.

-   :py:mod:`imas.dd_helpers` handles building the ``IDSDef.zip`` file, containing all
    versions of the Data Dictionary since ``3.22.0``.

-   :py:mod:`imas.dd_zip` handles loading the Data Dictionary definitions at run time.
    These definitions can be loaded from an ``IDSDef.zip`` or from a custom XML file.


.. _imas_architecture/IDS_nodes:

IDS nodes
---------

The following submodules and classes represent IDS nodes.

-   :py:mod:`imas.ids_base` defines the base class for all IDS nodes:
    :py:class:`~imas.ids_base.IDSBase`. This class is an abstract class and shouldn't
    be instantiated directly.

    Several useful properties are defined in this class, which are therefore available
    on any IDS node:

    -   ``_time_mode`` returns the ``ids_properties/homogeneous_time`` node
    -   ``_parent`` returns the parent object. Some examples:

        .. code-block:: python

            >>> core_profiles = imas.IDSFactory().core_profiles()
            >>> core_profiles._parent
            <imas.ids_factory.IDSFactory object at 0x7faa06bfac70>
            >>> core_profiles.ids_properties._parent
            <IDSToplevel (IDS:core_profiles)>
            >>> core_profiles.ids_properties.homogeneous_time._parent
            <IDSStructure (IDS:core_profiles, ids_properties)>
            >>> core_profiles.profiles_1d.resize(1)
            >>> core_profiles.profiles_1d[0]._parent
            <IDSStructArray (IDS:core_profiles, profiles_1d with 1 items)>
            >>> core_profiles.profiles_1d[0].time._parent
            <IDSStructure (IDS:core_profiles, profiles_1d[0])>

    -   ``_dd_parent`` returns the "data-dictionary" parent. This is usually the same as
        the ``_parent``, except for Arrays of Structures:

        .. code-block:: python

            >>> core_profiles = imas.IDSFactory().core_profiles()
            >>> core_profiles._dd_parent
            <imas.ids_factory.IDSFactory object at 0x7faa06bfac70>
            >>> core_profiles.ids_properties._dd_parent
            <IDSToplevel (IDS:core_profiles)>
            >>> core_profiles.ids_properties.homogeneous_time._dd_parent
            <IDSStructure (IDS:core_profiles, ids_properties)>
            >>> core_profiles.profiles_1d.resize(1)
            >>> # Note: _dd_parent for this structure is different from its parent:
            >>> core_profiles.profiles_1d[0]._dd_parent
            <IDSStructure (IDS:core_profiles, ids_properties)>
            >>> core_profiles.profiles_1d[0].time._dd_parent
            <IDSStructure (IDS:core_profiles, profiles_1d[0])>

    -   ``_path`` gives the path to this IDS node, including Array of Structures
        indices.
    -   ``_lazy`` indicates if the IDS is lazy loaded.
    -   ``_version`` is the Data Dictionary version of this node.
    -   ``_toplevel`` is a shortcut to the :py:class:`~imas.ids_toplevel.IDSToplevel`
        element that this node is a decendent of.

-   :py:mod:`imas.ids_primitive` contains all data node classes, which are child
    classes of :py:class:`~imas.ids_primitive.IDSPrimitive`. ``IDSPrimitive``
    implements all functionality that is common for every data type, whereas the
    classes in below list are specific per data type.

    Assignment-time data type checking is handled by the setter of the
    :py:attr:`~imas.ids_primitive.IDSPrimitive.value` property and the ``_cast_value``
    methods on each of the type specialization classes.

    -   :py:class:`~imas.ids_primitive.IDSString0D` is the type specialization for 0D
        strings. It can be used as if it is a python :external:py:class:`str` object.
    -   :py:class:`~imas.ids_primitive.IDSString1D` is the type specialization for 1D
        strings. It behaves as if it is a python :external:py:class:`list` of
        :external:py:class:`str`.
    -   :py:class:`~imas.ids_primitive.IDSNumeric0D` is the base class for 0D
        numerical types:

        -   :py:class:`~imas.ids_primitive.IDSComplex0D` is the type specialization
            for 0D complex numbers. It can be used as if it is a python
            :external:py:class:`complex`.
        -   :py:class:`~imas.ids_primitive.IDSFloat0D` is the type specialization
            for 0D floating point numbers. It can be used as if it is a python
            :external:py:class:`float`.
        -   :py:class:`~imas.ids_primitive.IDSInt0D` is the type specialization
            for 0D whole numbers. It can be used as if it is a python
            :external:py:class:`int`.

    -   :py:class:`~imas.ids_primitive.IDSNumericArray` is the type specialization for
        any numeric type with at least one dimension. It can be used as if it is a
        :external:py:class:`numpy.ndarray`.

-   :py:mod:`imas.ids_struct_array` contains the
    :py:class:`~imas.ids_struct_array.IDSStructArray` class, which models Arrays of
    Structures. It also contains some :ref:`dev lazy loading` logic.

-   :py:mod:`imas.ids_structure` contains the
    :py:class:`~imas.ids_structure.IDSStructure` class, which models Structures. It
    contains the :ref:`lazy instantiation` logic and some of the :ref:`dev lazy loading`
    logic.

-   :py:mod:`imas.ids_toplevel` contains the
    :py:class:`~imas.ids_toplevel.IDSToplevel` class, which is a subclass of
    :py:class:`~imas.ids_structure.IDSStructure` and models toplevel IDSs.

    It implements some API methods that are only available on IDSs, such as
    ``validate`` and ``(de)serialize``, and overwrites implementations of some
    properties.


.. _`lazy instantiation`:

Lazy instantiation
''''''''''''''''''

IDS nodes are instantiated only when needed. This is handled by
``IDSStructure.__getattr__``. When a new IDS Structure is created, it initially doesn't
have any IDS child nodes instantiated:

.. code-block:: python

    >>> import imas
    >>> # Create an empty IDS
    >>> cp = imas.IDSFactory().core_profiles()
    >>> # Show which elements are already created:
    >>> list(cp.__dict__)
    ['_lazy', '_children', '_parent', 'metadata', '__doc__', '_lazy_context']
    >>> # When we request a child element, it is automatically created:
    >>> cp.time
    <IDSNumericArray (IDS:core_profiles, time, empty FLT_1D)>
    >>> list(cp.__dict__)
    ['_lazy', '_children', '_parent', 'metadata', '__doc__', '_lazy_context',
     'time', '_toplevel']

This improves performance by creating fewer python objects: in most use cases, only a
subset of the nodes in an IDS will be used. These use cases benefit a lot from lazy
instantiation.


.. _`dev lazy loading`:

Lazy loading
''''''''''''

:ref:`lazy loading` defers reading the data from the backend in a
:py:meth:`~imas.db_entry.DBEntry.get` or :py:meth:`~imas.db_entry.DBEntry.get_slice`
until the data is requested. This is handled in two places:

1.  ``IDSStructure.__getattr__`` implements the lazy loading alongside the lazy
    instantiation. When a new element is created by lazy instantiation, it will call
    ``imas.db_entry_helpers._get_child`` to lazy load this element:

    -   When the element is a data node (``IDSPrimitive`` subclass), the data for this
        element is loaded from the backend.
    -   When the element is another structure, nothing needs to be loaded from the
        backend. Instead, we store the ``context`` on the created ``IDSStructure`` and
        data loading is handled recursively when needed.
    -   When the element is an Array of Structures, we also only store the ``context``
        on the created ``IDSStructArray``. Loading is handled as described in point 2.

2.  ``IDSStructArray._load`` implements the lazy loading of array of structures and
    their elements. This is triggered whenever an element is accessed (``__getitem__``)
    or the size of the Array of Structures is requested (``__len__``).


Creating and loading IDSs
-------------------------

-   :py:mod:`imas.db_entry` contains the :py:class:`~imas.db_entry.DBEntry` class.
    This class represents an on-disk Data Entry and can be used to store
    (:py:meth:`~imas.db_entry.DBEntry.put`,
    :py:meth:`~imas.db_entry.DBEntry.put_slice`) or load
    (:py:meth:`~imas.db_entry.DBEntry.get`,
    :py:meth:`~imas.db_entry.DBEntry.get_slice`) IDSs. The actual implementation of
    data storage and retrieval is handled by the backends in the
    ``imas.backends.*`` subpackages.

    :py:class:`~imas.db_entry.DBEntry` handles the autoconversion between IDS versions
    as described in :ref:`Automatic conversion between DD versions`.
-   :py:mod:`imas.ids_factory` contains the :py:class:`~imas.ids_factory.IDSFactory`
    class. This class is responsible for creating IDS toplevels from a given Data
    Dictionary definition, and can list all IDS names inside a DD definition.


Access Layer interfaces
-----------------------

-   :py:mod:`imas.backends.imas_core.al_context` provides an object-oriented interface when working with
    Lowlevel contexts. The contexts returned by the lowlevel are an integer identifier
    and need to be provided to several LL methods (e.g. ``read_data``), some of which
    may create new contexts.
    
    The :py:class:`~imas.backends.imas_core.al_context.ALContext` class implements this object oriented
    interface.

    A second class (:py:class:`~imas.backends.imas_core.al_context.LazyALContext`) implements the same
    interface, but is used when :ref:`dev lazy loading`.
-   :py:mod:`imas.ids_defs` provides access to Access Layer constants 
-   :py:mod:`imas.backends.imas_core.imas_interface` provides a version-independent interface to the
    Access Layer through :py:class:`~imas.backends.imas_core.imas_interface.LowlevelInterface`. It
    defines all known methods of the Access Layer and defers to the correct
    implementation if it is available in the loaded AL version (and raises a descriptive
    exception if the function is not available).


MDSplus support
---------------

-   :py:mod:`imas.backends.imas_core.mdsplus_model` is responsible for creating MDSplus `models`. These
    models are specific to a DD version and are required when using the MDSplus
    backend for creating new Data Entries.

    .. seealso:: :ref:`MDSplus in imas-python`


Versioning
----------

imas-python uses `setuptools-scm <https://pypi.org/project/setuptools-scm/>`_ for
versioning. An imas-python release has a corresponding tag (which sets the version).
The ``imas._version`` module is generated by ``setuptools-scm`` and implements this logic
for editable installs. This module is generated by ``setuptools-scm`` when building python
packages.


Conversion between Data Dictionary versions
-------------------------------------------

:py:mod:`imas.ids_convert` contains logic for converting an IDS between DD versions.

The :py:class:`~imas.ids_convert.DDVersionMap` class creates and contains mappings for
an IDS between two Data Dictionary versions. It creates two mappings: one to be used
when converting from the newer version of the two to the older version (``new_to_old``)
and a map for the reverse (``old_to_new``). These mappings are of type
:py:class:`~imas.ids_convert.NBCPathMap`. See its API documentation for more details.

:py:func:`~imas.ids_convert.convert_ids` is the main API method for converting IDSs
between versions. It works as follows:

-   It builds a ``DDVersionMap`` between the two DD versions version and selects the
    correct ``NBCPathMap`` (``new_to_old`` or ``old_to_new``).
-   If needed, it creates a target IDS of the destination DD version.
-   It then uses the ``NBCPathMap`` to convert data and store it in the target IDS.

:py:class:`~imas.db_entry.DBEntry` can also handle automatic DD version conversion. It
uses the same ``DDVersionMap`` and ``NBCPathMap`` as
:py:func:`~imas.ids_convert.convert_ids`. When reading data from the backends, the
``NBCPathMap`` is used to translate between the old and the new DD version. See the
implementation in :py:mod:`imas.backends.imas_core.db_entry_helpers`.


Miscelleneous
-------------

The following is a list of miscelleneous modules, which don't belong to any of the other
categories on this page.

-   :py:mod:`imas.exception` contains all Exception classes that imas-python may raise.
-   :py:mod:`imas.setup_logging` initializes a logging handler for imas-python.
-   :py:mod:`imas.training` contains helper methods for making training data
    available.
-   :py:mod:`imas.util` contains useful utility methods. It is imported automatically.

    All methods requiring third party libraries (``rich`` and ``scipy``) are implemented
    in ``imas._util``. This avoids importing these libraries immediately when a
    user imports ``imas`` (which can take a couple hundred milliseconds). Instead,
    this module is only loaded when a user needs this functionality.
