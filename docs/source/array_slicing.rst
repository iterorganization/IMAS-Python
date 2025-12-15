.. _array-slicing:

Array Slicing
=============

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
    
    # Access nested arrays
    all_ions = cp.profiles_1d[:].ion[:]  # IDSSlice of individual ions
    
    # Extract values
    labels = all_ions.label.values()

Multi-Dimensional Slicing
---------------------------

The ``IDSSlice`` class supports multi-dimensional shape tracking and array conversion.

**Check shape of sliced data:**

.. code-block:: python

    # Get shape information for multi-dimensional data
    print(cp.profiles_1d[:].grid.shape)              # (106,)
    print(cp.profiles_1d[:].ion.shape)               # (106, ~3)
    print(cp.profiles_1d[1:3].ion[0].element.shape)  # (2, ~3)

**Extract values with shape preservation:**

.. code-block:: python

    # Extract as list
    grid_values = cp.profiles_1d[:].grid.values()
    
    # Extract as numpy array
    grid_array = cp.profiles_1d[:].grid.to_array()
    
    # Extract as numpy array
    ion_array = cp.profiles_1d[:].ion.to_array() 

**Nested structure access:**

.. code-block:: python

    # Access through nested arrays
    grid_data = cp.profiles_1d[1:3].grid.rho_tor.to_array()
    
    # Ion properties across multiple profiles
    ion_labels = cp.profiles_1d[:].ion[:].label.to_array()
    ion_charges = cp.profiles_1d[:].ion[:].z_ion.to_array()

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
    
    # Or as numpy array
    times_array = cp.profiles_1d[:].time.to_array()

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

Both individual indexing and slicing work with lazy loading:

.. code-block:: python

    element = lazy_array[0]      # OK - loads on demand
    subset = lazy_array[1:5]     # OK - loads only requested elements on demand

When slicing lazy-loaded arrays, only the elements in the slice range are loaded,
making it memory-efficient for large datasets.
