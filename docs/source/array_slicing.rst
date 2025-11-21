Array Slicing
==============

The ``IDSStructArray`` class supports Python's standard slicing syntax.

Key Difference
---------------

- ``array[0]`` returns ``IDSStructure`` (single element)
- ``array[:]`` or ``array[1:5]`` returns ``IDSSlice`` (collection with ``values()`` method)

Basic Usage
-----------

.. code-block:: python

    import imas
    
    entry = imas.DBEntry("imas:hdf5?path=my-testdb")
    cp = entry.get("core_profiles")
    
    # Integer indexing
    first = cp.profiles_1d[0]           # IDSStructure
    last = cp.profiles_1d[-1]           # IDSStructure
    
    # Slice operations
    subset = cp.profiles_1d[1:5]        # IDSSlice
    every_other = cp.profiles_1d[::2]   # IDSSlice
    
    # Access nested arrays (automatic array-wise indexing)
    all_ions = cp.profiles_1d[:].ion[:]  # IDSSlice of individual ions
    
    # Extract values
    labels = all_ions.label.values()

Common Patterns
---------------

**Process a range:**

.. code-block:: python

    for element in cp.profiles_1d[5:10]:
        print(element.time)

**Iterate over nested arrays:**

.. code-block:: python

    for ion in cp.profiles_1d[:].ion[:]:
        print(ion.label.value)

**Get all values:**

.. code-block:: python

    times = cp.profiles_1d[:].time.values()

Important: Array-wise Indexing
-------------------------------

When accessing attributes through a slice of ``IDSStructArray`` elements,
the slice operation automatically applies to each array (array-wise indexing):

.. code-block:: python

    # Array-wise indexing: [:] applies to each ion array
    all_ions = cp.profiles_1d[:].ion[:]
    labels = all_ions.label.values()
    
    # Equivalent to manually iterating:
    labels = []
    for profile in cp.profiles_1d[:]:
        for ion in profile.ion:
            labels.append(ion.label.value)

Lazy-Loaded Arrays
-------------------

Individual indexing works with lazy loading, but slicing doesn't:

.. code-block:: python

    element = lazy_array[0]      # OK - loads on demand
    subset = lazy_array[1:5]     # ValueError
