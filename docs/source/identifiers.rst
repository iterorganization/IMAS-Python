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
- These may have alternative naming conventions supported through aliases 
  (e.g., "235U" and "U_235" for Uranium 235).

Identifiers are a list of possible valid labels. Each label has up to four
representations:

1. An index (integer)
2. A name (short string)
3. A description (long string)
4. List of aliases (list of short strings)


Identifiers in IMAS-Python
--------------------------

IMAS-Python implements identifiers as an :py:class:`enum.Enum`. Identifiers are
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

    # Access identifiers with aliases (when available)
    mid = imas.identifiers.materials_identifier
    print(mid["235U"].name)        # Access by canonical name
    print(mid["U_235"].name)       # Access by alias
    
    # Both return the same object
    assert mid["235U"].name is mid["U_235"].name
    assert mid["235U"].name is mid.U_235.name

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


Assigning identifiers in IMAS-Python
------------------------------------

IMAS-Python implements smart assignment of identifiers. You may assign an identifier
enum value (for example ``imas.identifiers.core_source_identifier.total``), a
string (for example ``"total"`` or its alias), or an integer (for example ``"1"``) 
to an identifier structure (for example ``core_profiles.source[0].identifier``) to set
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

    # Identifiers can still be assigned with the old alias name for backward compatibility:
    wallids = imas.IDSFactory().wall()
    wallids.description_ggd.resize(1)
    wallids.description_ggd[0].material.resize(1)
    wallids.description_ggd[0].material[0].grid_subset.resize(1)
    mat = wallids.description_ggd[0].material[0].grid_subset[0].identifiers
    mat.names.extend([""] * 1)
    mid = imas.identifiers.materials_identifier
    # Assign using canonical name
    mat.names[0] = "235U"
    # Or assign using alias (equivalent to above)
    mat.names[0] = mid["U_235"].name
    mat.names[0] = mid.U_235.name

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


Identifier aliases
------------------

Some identifiers may have multiple aliases defined in the Data Dictionary. Aliases are
former names kept as an option to ensure better backward compatibility after a change
and support multiple naming conventions. An identifier can have any number of
comma-separated aliases.

Aliases can be accessed in the same ways as canonical names, and all aliases for an
identifier point to the same object.

Aliases that begin with a number (e.g., 235U) cannot be accessed using dot notation 
(e.g., material_identifier.235U) due to Python's syntax restrictions. Instead, such
aliases must be accessed using dictionary-style indexing, for example:
material_identifier["235U"].

.. code-block:: python
    :caption: Working with identifier aliases

    import imas

    # Get materials identifier which has some aliases defined
    mid = imas.identifiers.materials_identifier
    
    # Access by canonical name
    uranium235_by_name = mid["235U"]
    print(f"Name: {uranium235_by_name.name}")
    print(f"Aliases: {uranium235_by_name.aliases}")  # List of all aliases
    print(f"First alias: {uranium235_by_name.alias}")  # First alias for compatibility
    print(f"Index: {uranium235_by_name.index}")
    print(f"Description: {uranium235_by_name.description}")
    
    # Access by any alias - all return the same object
    uranium235_by_alias1 = mid["U_235"].name
    uranium235_by_alias2 = mid["Uranium_235"].name
    print(f"Same objects: {uranium235_by_name is uranium235_by_alias1 is uranium235_by_alias2}")
    
    # You can also use attribute access for aliases (when valid Python identifiers)
    uranium235_by_attr = mid.U_235.name
    print(f"Same object: {uranium235_by_name is uranium235_by_attr}")
    
    # When assigning to IDS structures, alias works the following way
    wallids = imas.IDSFactory().wall()
    wallids.description_ggd.resize(1)
    wallids.description_ggd[0].material.resize(1)
    wallids.description_ggd[0].material[0].grid_subset.resize(1)
    mat = wallids.description_ggd[0].material[0].grid_subset[0].identifiers
    mat.names.extend([""] * 1)
    mat.indices.resize(1)
    mat.descriptions.extend([""] * 1)
    mat.indices[0] = 20
    mat.descriptions[0] = "Uranium 235 isotope"
    
    # These assignments are all equivalent:
    mat.names[0] = "235U"          # canonical name
    mat.names[0] = mid["235U"].name  # enum value
    mat.names[0] = mid.U_235.name  # enum value via alias
    mat.names[0] = mid["U_235"].name  # enum value via alias

Compare identifiers
-------------------

Identifier structures can be compared against the identifier enum as well. They
compare equal when:

1.  ``index`` is an exact match
2.  ``name`` is an exact match, or ``name`` matches an alias, or ``name`` is not filled in the IDS node

The ``description`` does not have to match with the Data Dictionary definition,
but a warning is logged if the description in the IDS node does not match with
the Data Dictionary description. The comparison also takes aliases into account,
so an identifier will match both its canonical name and any defined alias:

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
    >>> # Alias comparison example with materials identifier
    >>> mid = imas.identifiers.materials_identifier
    >>> cxr = imas.IDSFactory().camera_x_rays()
    >>> mat = cxr.filter_window.material
    >>> mat.index = 20
    >>> mat.name = "U_235"  # Using alias
    >>> # Compares equal to the canonical identifier even though name is alias
    >>> mat == mid["235U"].name
    True


.. seealso::

    -   :py:class:`imas.ids_identifiers.IDSIdentifier`: which is the base class
        of all identifier enumerations.
    -   :py:data:`imas.ids_identifiers.identifiers`: identifier accessor.
    -   :py:attr:`imas.ids_metadata.IDSMetadata.identifier_enum`: get the
        identifier enum from an IDS node.
