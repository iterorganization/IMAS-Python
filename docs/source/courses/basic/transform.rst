Transform with imas-python
==========================

In this part of the course we'll perform a coordinate transformation. Our input data is
in rectilinear :math:`R, Z` coordinates, which we will transform into poloidal polar
coordinates (:math:`\rho, \theta`) then store in a separate data entry.

Our strategy for doing this will be:

#. Check which time slices exist
#. The actual processing is done per time slice to limit memory consumption:

   #. Load the time slice
   #. Apply the coordinate transformation
   #. Store the time slice


Exercise 1: Check which time slices exist
-----------------------------------------

.. md-tab-set::

    .. md-tab-item:: Exercise

        Load the time array from the ``equilibrium`` IDS in the training data entry.

        .. hint::
            You can use :ref:`lazy loading` to avoid loading all data in memory.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/transform_grid.py
            :start-at: # Open input data entry
            :end-before: # Create output data entry


Exercise 2: Load a time slice
-----------------------------

.. md-tab-set::

    .. md-tab-item:: Exercise

        Loop over each available time in the IDS and load the time slice inside the
        loop.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/transform_grid.py
            :start-at: # Loop over each time slice
            :end-before: # Update comment


Exercise 3: Apply the transformation
------------------------------------

We will apply the transformation of the data as follows:

#.  Load the :math:`R,Z` grid from the time slice
#.  Generate a new :math:`\rho,\theta` grid
#.  Calculate the rectilinear coordinates belonging to the :math:`\rho,\theta` grid:

    .. math::

        R = R_\mathrm{axis} + \rho \cos(\theta)

        Z = Z_\mathrm{axis} + \rho \sin(\theta)

#.  For each data element, interpolate the data on the new grid. We can use
    :external:class:`scipy.interpolate.RegularGridInterpolator` for this.
#.  Finally, we store the new grid (including their rectilinear coordinates) and the
    transformed data in the IDS


.. md-tab-set::

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/transform_grid.py
            :start-at: # Loop over each time slice
            :end-before: # Finally, put the slice to disk


Exercise 4: Store a time slice
------------------------------

.. md-tab-set::

    .. md-tab-item:: Exercise

        Store the time slice after the transformation.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/transform_grid.py
            :start-at: # Create output data entry
            :end-at: output_entry.create()
            :caption: The data entry is created once, outside the time slice loop

        .. literalinclude:: imas_snippets/transform_grid.py
            :start-at: # Finally, put the slice to disk
            :end-at: output_entry.put_slice
            :caption: Store the time slice inside the loop


Exercise 5: Plotting data before and after the transformation
-------------------------------------------------------------

.. md-tab-set::

    .. md-tab-item:: Exercise

        Plot one of the data fields in the :math:`R, Z` plane (original data) and in the
        :math:`\rho,\theta` plane (transformed data) to verify that the transformation
        is correct.

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/transform_grid.py
            :start-at: # Create a plot


Bringing it all together
------------------------

.. md-tab-set::

    .. md-tab-item:: imas-python

        .. literalinclude:: imas_snippets/transform_grid.py
            :caption: Source code for the complete exercise
