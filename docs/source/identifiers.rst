.. _`Identifiers`:

Identifiers
===========

The "identifier" structure is used by the Data Dictionary to provide an
enumerated list of options for defining, for example:

- A particular coordinate system, such as Cartesian, cylindrical, or spherical.
- A particle, which may be either an electron, an ion, a neutral atom, a molecule,
  a neutron, or a photon.
- Plasma heating may come from neutral beam injection, electron cyclotron heating,
  ion cyclotron heating, lower hybrid heating, alpha particles.

Identifiers are a list of possible valid labels. Each label has three
representations:

1. An index (integer)
2. A name (short string)
3. A description (long string)


Identifiers in imas-python
--------------------------

imas-python implements identifiers as an :py:class:`enum.Enum`. Identifiers are
constructed on-demand from the loaded Data Dictionary definitions.

All identifier enums can be accessed through ``imas.identifiers``. A list of
the available identifiers is stored as ``imas.identifiers.identifiers``.

.. code-block:: python
    :caption: Accessing identifiers

    import imas

    # List all identifier names
    for identifier_name in imas.identifiers.identifiers:
        print(identifier_name)
    # Get a specific identifier
    csid = imas.identifiers.core_source_identifier
    # Get and print information of an identifier value
    print(csid.total)
    print(csid.total.index)
    print(csid.total.description)

    # Item access is also possible
    print(identifiers["edge_source_identifier"])

    # You can use imas.util.inspect to list all options
    imas.util.inspect(identifiers.ggd_identifier)
    # And also to get more details of a specific option
    imas.util.inspect(identifiers.ggd_identifier.SN)

    # When an IDS node is an identifier, you can use
    # metadata.identifier_enum to get the identifier
    core_sources = imas.IDSFactory().core_sources()
    core_sources.source.resize(1)
    print(core_sources.source[0].identifier.metadata.identifier_enum)


Assigning identifiers in imas-python
------------------------------------

imas-python implements smart assignment of identifiers. You may assign an identifier
enum value (for example ``imas.identifiers.core_source_identifier.total``), a
string (for example ``"total"``) or an integer (for example ``"1"``) to an
identifier structure (for example ``core_profiles.source[0].identifier``) to set
all three child nodes ``name``, ``index`` and ``description`` in one go. See
below example:

.. code-block:: python
    :caption: Assigning identifiers

    import imas

    core_sources = imas.IDSFactory().core_sources()
    core_sources.source.resize(2)

    csid = imas.identifiers.core_source_identifier
    # We can set the identifier in three ways:
    # 1. Assign an instance of the identifier enum:
    core_sources.source[0].identifier = csid.total
    # 2. Assign a string. This looks up the name in the identifier enum:
    core_sources.source[0].identifier = "total"
    # 3. Assign an integer. This looks up the index in the identifier enum:
    core_sources.source[0].identifier = 1

    # Inspect the contents of the structure
    imas.util.inspect(core_sources.source[0].identifier)

    # You can still assign any value to the individual name / index /
    # description nodes:
    core_sources.source[1].identifier.name = "total"
    # Only name is set, index and description are empty
    imas.util.inspect(core_sources.source[1].identifier)
    # This also allows to use not-yet-standardized identifier values
    core_sources.source[1].identifier.name = "my_custom_identifier"
    core_sources.source[1].identifier.index = -1
    core_sources.source[1].identifier.description = "My custom identifier"
    imas.util.inspect(core_sources.source[1].identifier)


Compare identifiers
-------------------

Identifier structures can be compared against the identifier enum as well. They
compare equal when:

1.  ``index`` is an exact match
2.  ``name`` is an exact match, or ``name`` is not filled in the IDS node

The ``description`` does not have to match with the Data Dictionary definition,
but a warning is logged if the description in the IDS node does not match with
the Data Dictionary description:

.. code-block:: python
    :caption: Comparing identifiers

    >>> import imas
    >>> csid = imas.identifiers.core_source_identifier
    >>> core_sources = imas.IDSFactory().core_sources()
    >>> core_sources.source.resize(1)
    >>> core_sources.source[0].identifier.index = 1
    >>> # Compares equal to csid.total, though name and description are empty
    >>> core_sources.source[0].identifier == csid.total
    True
    >>> core_sources.source[0].identifier.name = "total"
    >>> # Compares equal to csid.total, though description is empty
    >>> core_sources.source[0].identifier == csid.total
    True
    >>> core_sources.source[0].identifier.description = "INVALID"
    >>> # Compares equal to csid.total, though description does not match
    >>> core_sources.source[0].identifier == csid.total
    13:24:11 WARNING  Description of <IDSString0D (IDS:core_sources, source[0]/identifier/description, STR_0D)>
    str('INVALID') does not match identifier description 'Total source; combines all sources' @ids_identifiers.py:46
    True
    >>> # Does not compare equal when index matches but name does not
    >>> core_sources.source[0].identifier.name = "totalX"
    >>> core_sources.source[0].identifier == csid.total
    False


.. seealso::

    -   :py:class:`imas.ids_identifiers.IDSIdentifier`: which is the base class
        of all identifier enumerations.
    -   :py:data:`imas.ids_identifiers.identifiers`: identifier accessor.
    -   :py:attr:`imas.ids_metadata.IDSMetadata.identifier_enum`: get the
        identifier enum from an IDS node.
