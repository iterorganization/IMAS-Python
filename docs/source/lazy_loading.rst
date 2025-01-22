.. _`Lazy loading`:

Lazy loading
============

When reading data from a data entry (using :meth:`DBEntry.get
<imas.db_entry.DBEntry.get>`, or :meth:`DBEntry.get_slice
<imas.db_entry.DBEntry.get_slice>`), by default all data is read immediately from the
lowlevel Access Layer backend. This may take a long time to complete if the data entry
has a lot of data stored for the requested IDS.

Instead of reading data immediately, imas-python can also `lazy load` the data when you need
it. This will speed up your program in cases where you are interested in a subset of all
the data stored in an IDS.


Enable lazy loading of data
---------------------------

You can enable lazy loading of data by supplying the keyword argument :code:`lazy=True`
to :meth:`DBEntry.get <imas.db_entry.DBEntry.get>`, or :meth:`DBEntry.get_slice
<imas.db_entry.DBEntry.get_slice>`. The returned IDS
object will fetch the data from the backend at the moment that you want to access it.
See below example:

.. literalinclude:: courses/basic/imas_snippets/plot_core_profiles_te.py
    :caption: Example with lazy loading of data

In this example, using lazy loading with the MDSPLUS backend is about 12 times
faster than a regular :code:`get()`. When using the HDF5 backend, lazy loading
is about 300 times faster for this example.


Caveats of lazy loaded IDSs
---------------------------

Lazy loading of data may speed up your programs, but also comes with some limitations.

1.  Some functionality is not implemented or works differently for lazy-loaded IDSs:

    -   Iterating over non-empty nodes works differently, see API documentation:
        :py:meth:`imas.ids_structure.IDSStructure.iter_nonempty_`.
    -   :py:meth:`~imas.ids_structure.IDSStructure.has_value` is not implemented for
        lazy-loaded structure elements.
    -   :py:meth:`~imas.ids_toplevel.IDSToplevel.validate` will only validate loaded
        data. Additional data might be loaded from the backend to validate coordinate
        sizes.
    -   :py:meth:`imas.util.print_tree` will only print data that is loaded when
        :py:param:`~imas.util.print_tree.hide_empty_nodes` is ``True``.
    -   :py:meth:`imas.util.visit_children`:

        -   When :py:param:`~imas.util.visit_children.visit_empty` is ``False``
            (default), this method uses
            :py:meth:`~imas.ids_structure.IDSStructure.iter_nonempty_`. This raises an
            error for lazy-loaded IDSs, unless you set
            :py:param:`~imas.util.visit_children.accept_lazy` to ``True``.
        -   When :py:param:`~imas.util.visit_children.visit_empty` is ``True``, this
            will iteratively load `all` data from the backend. This is effectively a
            full, but less efficient, ``get()``\ /\ ``get_slice()``. It will be faster
            if you don't use lazy loading in this case.

    -   IDS conversion through :py:meth:`imas.convert_ids
        <imas.ids_convert.convert_ids>` is not implemented for lazy loaded IDSs. Note
        that :ref:`Automatic conversion between DD versions` also applies when lazy
        loading.
    -   Lazy loaded IDSs are read-only, setting or changing values, resizing arrays of
        structures, etc. is not allowed.
    -   You cannot :py:meth:`~imas.db_entry.DBEntry.put`,
        :py:meth:`~imas.db_entry.DBEntry.put_slice` or
        :py:meth:`~imas.ids_toplevel.IDSToplevel.serialize` lazy-loaded IDSs.
    -   Copying lazy-loaded IDSs (through :external:py:func:`copy.deepcopy`) is not
        implemented.

2.  imas-python **assumes** that the underlying data entry is not modified.

    When you (or another user) overwrite or add data to the same data entry, you may end
    up with a mix of old and new data in the lazy loaded IDS.

3.  After you close the data entry, no new elements can be loaded.

    >>> core_profiles = data_entry.get("core_profiles", lazy=True)
    >>> data_entry.close()
    >>> print(core_profiles.time)
    Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
    RuntimeError: Cannot lazy load the requested data: the data entry is no longer
    available for reading. Hint: did you close() the DBEntry?

4.  Lazy loading has more overhead for reading data from the lowlevel: it is therefore
    more efficient to do a full :code:`get()` or :code:`get_slice()` when you intend to
    use most of the data stored in an IDS.
5.  When using imas-python with remote data access (i.e. the UDA backend), a full
    :code:`get()` or :code:`get_slice()` is more efficient than lazy loading.
