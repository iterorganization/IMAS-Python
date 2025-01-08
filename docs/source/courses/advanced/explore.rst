Advanced data exploration
=========================

In the :ref:`basic/explore` training we have seen how to explore imas-python data structures
in an interactive way.

In this lesson, we will go a step further and look at methods to explore imas-python data
structures programmatically. This can be useful for, for example, writing plotting
tools, analysis scripts, etc.


Exploring IDS (sub)structures
-----------------------------

An IDS structure is a collection of IDS nodes (which could be structures, or arrays of
structures themselves). In imas-python this is represented by the
:py:class:`~imas.ids_structure.IDSStructure` class. You will find these classes in a
lot of places:

- Data Dictionary IDSs is a special case of an IDS structure (implemented by class
  :py:class:`~imas.ids_toplevel.IDSToplevel`, which is a subclass of
  ``IDSStructure``).
- Data Dictionary structures, for example, the ``ids_properties`` structure that is
  present in every IDS.
- Data Dictionary arrays of structures (implemented by
  :py:class:`~imas.ids_struct_array.IDSStructArray`) contain ``IDSStructure``\ s.

When you have an ``IDSStructure`` object, you can iterate over it to get all child nodes
that are contained in this structure. See the following example:

.. code-block:: python

    import imas

    core_profiles = imas.IDSFactory().core_profiles()
    # core_profiles is an IDS toplevel, which is also a structure:
    
    print("Core profiles contains the following elements:")
    for child_node in core_profiles:
        print("-", child_node.metadata.name)

    print()
    print("Core profiles contains the following non-empty elements:")
    # If you only want to loop over child nodes that have some data in them:
    for filled_child_node in core_profiles.iter_nonempty_():
        print("-", child_node.metadata.name)


Exercise 1: Explore structures
''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``equilibrium`` IDS. You can refresh how to
            do this in the following section of the basic training material: :ref:`Open
            an IMAS database entry`.
        2.  Loop over all non-empty child nodes of this IDS and print their name.
        3.  Print all child nodes of the ``ids_properties`` structure and their value.
        
    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/explore_structures.py


Explore IDS data nodes and arrays of structures
-----------------------------------------------

Besides structures, IDSs contain arrays of structures, and data nodes. Arrays of
structures (modeled by :py:class:`~imas.ids_struct_array.IDSStructArray`) are (as the
name applies) arrays containing :py:class:`~imas.ids_structure.IDSStructure`\ s. Data
nodes can contain scalar or array data of various types.

Some methods and properties are defined for all data nodes and arrays of structures:

``len(<node>)``
    Returns the length of the node:
    
    - For scalar numbers (``INT_0D``, ``FLT_0D`` and ``CPX_0D``) this will give an
      error.
    - For strings (``STR_0D``) this will give the length of the string.
    - For arrays (``STR_1D`` and ``ND`` numbers) this will give the length of the
      `first` dimension.

``<node>.has_value``
    This is ``True`` when a value is stored in the node.

``<node>.size``
    Get the number of elements that are stored in the underlying data.

    - For scalar types (``*_0D``) this is always 1.
    - For 1D arrays, the ``size`` is always the same as their length (see
      ``len(<node>)``).
    - For ND arrays, the ``size`` is equal to ``np.prod(<node>.shape)``: the product of
      the array's dimensions.

``<node>.shape``
    Get the shape of the underlying data.

    There are as many items as the rank of the data: ``len(<node>.snape) ==
    <node>.metadata.ndim``.

``<node>.coordinates``
    Get access to the coordinate values. See the :ref:`Using metadata` lesson for more
    details.

.. seealso::
    You can find more details on IDS data node related classes and methods in the imas-python Architecture documentation:
    :ref:`imas_architecture/IDS_nodes`

Apply a function to all nodes in an IDS
'''''''''''''''''''''''''''''''''''''''

Before diving into the exercise and use this new knowledge, it is useful to know the
:py:meth:`imas.util.visit_children` method. This method allows you to apply a method
to all nodes of an IDS. Additional keyword arguments can control whether you want to
include leaf nodes (data nodes) only, or also include structures and arrays of
structure. You can also choose between applying the function to filled nodes only (the
default) or all nodes, including empty ones.


.. seealso::
    You can find more details in the API documentation:
    :py:meth:`imas.util.visit_children`


Exercise 2: Explore data nodes
''''''''''''''''''''''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``equilibrium`` IDS.
        2.  Create a function that prints the path, shape and size of an IDS node.
        3.  Use :py:meth:`~imas.util.visit_children` to apply the function to all
            non-empty nodes in the equilbrium IDS.
        4.  Update your function such that it skips scalar (0D) IDS nodes. Apply the
            updated function to the equilibrium IDS.

        .. hint::
            :collapsible:
            
            Review imas-python Architecture documentation for data node methods:
            :ref:`imas_architecture/IDS_nodes`

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/explore_data.py
