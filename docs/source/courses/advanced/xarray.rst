Create ``xarray.DataArray`` from an IDS
=======================================

.. info::

    In this lesson you will create a ``DataArray`` manually. In a future version of
    imas-python we plan to include functionality that will automatically do this for you.
    That should further simplify working with data inside IDSs.

Let's start with an introduction of Xarray. According to `their website
<https://docs.xarray.dev/en/stable/getting-started-guide/why-xarray.html>`_ (where you
can also find an excellent summary of why that is useful):

.. quote::

    Xarray introduces labels in the form of dimensions, coordinates and attributes on
    top of raw NumPy-like multidimensional arrays, which allows for a more intuitive,
    more concise, and less error-prone developer experience.

In this lesson, we will use the :ref:`metadata <using metadata>` from the Data
Dictionary to construct a ``DataArray`` from an IDS.

.. note::

    This section uses the python package ``xarray``. This package can be installed by
    following `the instructions on their website
    <https://docs.xarray.dev/en/stable/getting-started-guide/installing.html>`_.


Exercise 1: create a ``DataArray`` for ``profiles_1d/temperature``
------------------------------------------------------------------

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``core_profiles`` IDS. You can refresh how to
            do this in the following section of the basic training material: :ref:`Open
            an IMAS database entry`.
        2.  Get the average ion temperature data of the first time slice of
            ``profiles_1d``.
        3.  To create a DataArray from this temperature data, we need to give the
            following items to ``xarray``:

            -   The data itself.
            -   The coordinates and their values as a Python dictionary
                ``{"coordinate_name": coordinate_value, [...]}``.
            -   Any additional attributes. For this example we add the ``units``.
            -   The name of the data.

            Get these values for our ``temperature`` array.
        4.  Create the ``xarray.DataArray``: :code:`xarray.DataArray(data,
            coords=coordinates, attrs=attributes, name=name)`. Print the data array.
        5.  Now we can use the ``xarray`` API. Let's try some examples:

            a.  Select all items where ``rho_tor_norm`` is between 0.4 and 0.6:
                ``temperature.sel(rho_tor_norm=slice(0.4, 0.6))``.
            b.  Interpolate the data to a different grid:
                ``temperature.interp(rho_tor_norm=numpy.linspace(0, 1, 11))``
            c.  Create a plot: ``temperature.plot()``

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/ids_to_xarray.py


Exercise 2: include the ``time`` axis in the ``DataArray``
----------------------------------------------------------

In the previous exercise we created a ``DataArray`` for a variable in one time slice of
the ``profiles_1d`` array of structures. When the grid is not changing in the IDS data
(``profiles_1d[i]/grid/rho_tor_norm`` is constant), it can be useful to construct a 2D
``DataArray`` with the ``time`` dimension:

.. md-tab-set::

    .. md-tab-item:: Exercise

        1.  Load the training data for the ``core_profiles`` IDS.
        2.  Get the average ion temperature data of the first time slice of
            ``profiles_1d``. Verify that the coordinates are the same for all time
            slices with ``numpy.allclose``.
        3.  Concatenate the data of all time slices: ``numpy.array([arr1, arr2, ...])``.
            Note that we have introduced an extra ``time`` coordinate now!
        4.  Create the ``DataArray`` and print it.
        5.  Now we can use the ``xarray`` API. Let's try some examples:

            a.  Select all items where ``rho_tor_norm`` is between 0.4 and 0.6:
                ``temperature.sel(rho_tor_norm=slice(0.4, 0.6))``.
            b.  Interpolate the data to a different grid:
                ``temperature.interp(rho_tor_norm=numpy.linspace(0, 1, 11))``
            c.  Interpolate the data to a different time base:
                ``temperature.interp(time=[10, 20])``
            d.  Create a 2D plot: ``temperature.plot(x="time",
                norm=matplotlib.colors.LogNorm())``

    .. md-tab-item:: Solution

        .. literalinclude:: imas_snippets/tensorized_ids_to_xarray.py
