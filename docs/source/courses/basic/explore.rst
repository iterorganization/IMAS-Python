.. _`basic/explore`:

Explore with imas-python
========================

In this part of the training, we will learn how to use Python to explore data
saved in IDSs.


Explore which IDSs are available
--------------------------------

Most codes will touch multiple IDSs inside a single IMAS data entry. For example
a heating code using a magnetic equilibrium from the ``equilibrium`` IDS with a
heating profile from the ``core_sources`` IDS. To find out how to write your
code, there are two main strategies: read the
`Data Model <https://confluence.iter.org/display/IMP/Data+Model>`_ documents of
the `Data Dictionary
<https://portal.iter.org/departments/POP/CM/IMDesign/Data%20Model/CI>`_
or explore the data interactively. We will focus on the latter method here.


Exercise 1
''''''''''

.. md-tab-set::

    .. md-tab-item:: Exercise

        Find out the names of the available IDSs.

        .. hint::
            The module ``imas.ids_names`` contains information on the available IDSs.

            In imas-python, you can use :py:class:`~imas.ids_factory.IDSFactory` to figure
            out which IDSs are avaible.

    .. md-tab-item:: imas-python
        
        .. literalinclude:: imas_snippets/print_idss.py


Explore the structure and contents of an IDS
--------------------------------------------

imas-python has several features and utilities for exploring an IDS. These are best used in
an interactive Python console, such as the default python console or the `IPython
<https://ipython.org/>`_ console.


Tab completion
''''''''''''''

As with most Python objects, you can use :kbd:`Tab` completion on imas-python objects.

.. note::
    In the python console, you need to press :kbd:`Tab` twice to show suggestions.

- :py:class:`~imas.ids_factory.IDSFactory` has tab completion for IDS names:

  .. code-block:: pycon

    >>> factory = imas.IDSFactory()
    >>> factory.core_
    factory.core_instant_changes(  factory.core_sources(
    factory.core_profiles(         factory.core_transport(

- :py:class:`~imas.ids_toplevel.IDSToplevel` and
  :py:class:`~imas.ids_structure.IDSStructure` have tab completion for child nodes:

  .. image:: interactive_tab_core_profiles_toplevel.png


Interactive help
''''''''''''''''

Use the built-in :external:py:func:`help()` function to get more information on imas-python
functions, objects, etc.

.. code-block:: pycon

    >>> import imas
    >>> help(imas.DBEntry)
    Help on class DBEntry in module imas.db_entry:

    class DBEntry(builtins.object)
    [...]


Inspecting imas-python objects
''''''''''''''''''''''''''''''

:kbd:`Tab` completion is nice when you already know more or less what attribute you are
looking for. For a more comprehensive overview of any imas-python node, you can use
:py:meth:`imas.util.inspect` to show:

1.  The path to the node (relative to the IDS it is contained in)
2.  The Data Dictionary version
3.  The documentation metadata from the Data Dictionary
4.  The `value` of the node (when applicable)
5.  Attributes of the node
6.  An overview of child nodes (when applicable)

.. hint::

    The output of :py:meth:`imas.util.inspect` is colored when your terminal supports
    it. You may use the environment variable ``NO_COLOR`` to disable colored output or
    ``FORCE_COLOR`` to force colored output. See
    `<https://rich.readthedocs.io/en/stable/console.html#environment-variables>`_.

    The exact colors your terminal shows are configurable and therefore may deviate from
    the colors in below screenshots.

.. rubric:: Examples

.. image:: imas_inspect.png


Printing an IDS tree
''''''''''''''''''''

Another useful utility function in imas-python is :py:meth:`imas.util.print_tree`. This
will print a complete tree structure of all non-empty quantities in the provided node.
As an argument you can give a complete IDS, or any structure in the IDS such as
``ids_properties``:

.. image:: print_tree_ids_properties.png

.. caution::

    Depending on the size of the IDS (structure) you print, this may generate a lot of
    output. For interactive exploration of large IDSs we recommend to use
    :py:meth:`imas.util.inspect` (optionally with the parameter ``hide_empty_nodes``
    set to :code:`True`) and only use :py:meth:`imas.util.print_tree` for smaller
    sub-structures.


Find paths in an IDS
''''''''''''''''''''

In imas-python you can also search for paths inside an IDS:
:py:meth:`imas.util.find_paths`. This can be useful when you know what quantity you
are looking for, but aren't sure exactly in which (sub)structure of the IDS it is
located.

:py:meth:`imas.util.find_paths` accepts any Python regular expression (see
:external:py:mod:`re`) as input. This allows for anything from basic to advanced
searches.

.. rubric:: Examples

.. literalinclude:: imas_snippets/find_paths.py


Exercise 2
----------

.. md-tab-set::

    .. md-tab-item:: Exercise

        Load some IDSs and interactively explore their contents. You can use any of the
        below suggestions (some require access to the Public ITER database), or use any
        you have around.

        Suggested data entries:

        - :ref:`Training data entry <Open an IMAS database entry>`, IDSs
          ``core_profiles`` or ``equilibrium``.
        - ITER machine description database, IDS ``pf_active``:

          .. code-block:: python

            backend = HDF5_BACKEND
            db_name, pulse, run, user = "ITER_MD", 111001, 103, "public"

        - ITER machine description database, IDS ``ec_launchers``:

          .. code-block:: python

            backend = HDF5_BACKEND
            db_name, pulse, run, user = "ITER_MD", 120000, 204, "public"

    .. md-tab-item:: Training data

        .. literalinclude:: imas_snippets/explore_training_data.py

    .. md-tab-item:: `pf_active` data

        .. literalinclude:: imas_snippets/explore_public_pf_active.py

    .. md-tab-item:: `ec_launchers` data

        .. literalinclude:: imas_snippets/explore_public_ec_launchers.py