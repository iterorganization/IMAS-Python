Array Slicing
==============

The ``IDSStructArray`` class supports Python's standard slicing syntax.

Key Difference
---------------

- ``array[0]`` returns ``IDSStructure`` (single element)
- ``array[:]`` or ``array[1:5]`` returns ``IDSSlice`` (collection with ``flatten()`` and ``values()``)

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
    
    # Flatten nested arrays
    all_ions = cp.profiles_1d[:].ion[:].flatten()  # IDSSlice of individual ions
    
    # Extract values
    labels = all_ions.label.values()

Common Patterns
---------------

**Process a range:**

.. code-block:: python

    for element in cp.profiles_1d[5:10]:
        print(element.time)

**Flatten and iterate:**

.. code-block:: python

    for ion in cp.profiles_1d[:].ion[:].flatten():
        print(ion.label.value)

**Get all values:**

.. code-block:: python

    times = cp.profiles_1d[:].time.values()

Important Constraint
--------------------

When accessing attributes through a slice, all elements must have that attribute. 
If elements are ``IDSStructArray`` objects, flatten first:

.. code-block:: python

    # Fails - IDSStructArray has no 'label' attribute
    # cp.profiles_1d[:].ion[:].label
    
    # Correct - flatten first
    labels = cp.profiles_1d[:].ion[:].flatten().label.values()

Lazy-Loaded Arrays
-------------------

Individual indexing works with lazy loading, but slicing doesn't:

.. code-block:: python

    element = lazy_array[0]      # OK - loads on demand
    subset = lazy_array[1:5]     # ValueError
