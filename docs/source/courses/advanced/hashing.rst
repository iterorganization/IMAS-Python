Calculating hashes of IMAS data
===============================

imas-python can calculate *hashes* of IMAS data. As `Wikipedia explains better than I could
do <https://en.wikipedia.org/wiki/Hash_function>`__:

    A hash function is any function that can be used to map data of arbitrary size to
    fixed-size values, [...]. The values returned by a hash function are called *hash
    values*, *hash codes*, *hash digests*, *digests*, or simply *hashes*.

imas-python is using the XXH3 hash function from the `xxHash project
<https://github.com/Cyan4973/xxHash>`__. This is a *non-cryptographic* hash and returns
64-bit hashes.


Use cases
---------

Hashes of IMAS data are probably most useful as *checksums*: when the hashes of two IDSs
match, there is `a very decent chance <https://en.wikipedia.org/wiki/Hash_collision>`__
that they contain identical data. [#collision]_ This can be useful to verify data
integrity, and detect whether data has been accidentally corrupted or altered.

.. [#collision] Note that it is possible to construct two IDSs that share the same
    *hash* but have completely different data. This is tricky and should be rare to
    occur.


Exercise 1: Calculate some hashes
---------------------------------

.. md-tab-set::

    .. md-tab-item:: Exercise

        In this exercise we will use :py:func:`imas.util.calc_hash` to calculate
        hashes of some IDSs. Use :external:py:meth:`bytes.hex` to show a more readable
        hexidecimal format of the hash.

        1.  Create an empty ``equilibrium`` IDS and print its hash.
        2.  Now fill ``ids_properties.homogeneous_time`` and print the hash. Did it
            change?
        3.  Resize the ``time_slice`` Array of Structures to size 2. Calculate the hash
            of ``time_slice[0]`` and ``time_slice[1]``. What do you notice?
        4.  Resize ``time_slice[0].profiles_2d`` to size 1. For convenience, you can
            create a variable ``p2d = time_slice[0].profiles_2d[0]``.
        5.  Fill ``p2d.r = [[1., 2.]]`` and ``p2d.z = p2d.r``, then calculate their
            hashes. What do you notice?
        6.  ``del p2d.z`` and calculate the hash of ``p2d``. Then set ``p2d.z = p2d.r``
            and ``del p2d.r``. What do you notice?

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/hashing.py


Properties of imas-python's hashes
----------------------------------

The implementation of the hash function has the following properties:

-   Only fields that are filled are included in the hash.

    If a newer version of the Data Dictionary introduces additional data fields, then
    this won't affect the hash of your data.

    As long as there are no Non Backwards Compatible changes in the Data Dictionary for
    the filled fields, the data hashes should not change.

-   The ``ids_properties/version_put`` structure is not included in the hash.

    This means that the precise Access Layer version, Data Dictionary version or high
    level interface that was used to store the data, does not affect the hash of the
    data.

-   Hashes are different for ND arrays with different shapes that share the same
    underlying data.

    For example, the following arrays are stored the same way in your RAM, but
    they result in different hashes:

    .. code-block:: python

        array1 = [1, 2]
        array2 = [[1, 2]]
        array3 = [[1],
                  [2]]


Technical details and specification
-----------------------------------

You can find the technical details, and a specification for calculating the hashes, in
the documentation of :py:meth:`imas.util.calc_hash`.
