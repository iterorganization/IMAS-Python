.. _`IDS validation`:

IDS validation
==============

The IDSs you fill should be consistent. To help you in validating that, imas-python has a
:py:meth:`~imas.ids_toplevel.IDSToplevel.validate` method that executes the following
checks.

.. contents:: Validation checks
    :local:
    :depth: 1

If you call this method and your IDS fails validation, imas-python raises an error explaining
the problem. See the following example:

>>> import imas
>>> core_profiles = imas.IDSFactory().core_profiles()
>>> core_profiles.validate()
imas.exception.ValidationError: Invalid value for ids_properties.homogeneous_time: -999999999

imas-python also automatically validates an IDS every time you do a
:py:meth:`~imas.db_entry.DBEntry.put` or
:py:meth:`~imas.db_entry.DBEntry.put_slice`. To disable this feature, you must set the
environment variable ``IMAS_AL_DISABLE_VALIDATE`` to ``1``.

.. seealso::
    
    API documentation: :py:meth:`IDSToplevel.validate() <imas.ids_toplevel.IDSToplevel.validate>`


Validate the time mode
----------------------

The time mode of an IDS is stored in ``ids_properties.homogeneous_time``.
This property must be filled with a valid time mode
(``IDS_TIME_MODE_HOMOGENEOUS``, ``IDS_TIME_MODE_HETEROGENEOUS`` or
``IDS_TIME_MODE_INDEPENDENT``). When the time mode is `independent`, all time-dependent
quantities must be empty.


Validate coordinates
--------------------

If a quantity in your IDS has coordinates, then these coordinates must be filled. The
size of your data must match the size of the coordinates:

.. todo:: link to DD docs

1.  Some dimensions must have a fixed size. This is indicated by the Data Dictionary
    as, for example, ``1...3``.

    For example, in the ``magnetics`` IDS, ``b_field_pol_probe(i1)/bandwidth_3db`` has
    ``1...2`` as coordinate 1. This means that, if you fill this data field, the first
    (and only) dimension of this field must be of size 2.

2.  If the coordinate is another quantity in the IDS, then that coordinate must be
    filled and have the same size as your data.

    For example, in the ``pf_active`` IDS, ``coil(i1)/current_limit_max`` is a
    two-dimensional quantity with coordinates ``coil(i1)/b_field_max`` and
    ``coil(i1)/temperature``. This means that, if you fill this data field, their
    coordinate fields must be filled as well. The first dimension of
    ``current_limit_max`` must have the same size as ``b_field_max`` and the second
    dimension the same size as ``temperature``. Expressed in Python code:

    .. code-block:: python

        numpy.shape(current_limit_max) == (len(b_field_max), len(temperature))

    Time coordinates are handled depending on the value of
    ``ids_properties/homogeneous_time``:

    -   When using ``IDS_TIME_MODE_HOMOGENEOUS``, all time coordinates look at the root
        ``time`` node of the IDS.
    -   When using ``IDS_TIME_MODE_HETEROGENOUS``, all time coordinates look at the time
        path specified as coordinate by the Data Dictionary.

        For dynamic array of structures, the time coordinates is a ``FLT_0D`` inside the
        AoS (see, for example, ``profiles_1d`` in the ``core_profiles`` IDS). In such
        cases the time node must be set to something different than ``EMPTY_FLOAT``.
        This is the only case in which values of the coordinates are verified, in all
        other cases only the sizes of coordinates are validated.

    .. rubric:: Alternative coordinates

    Version 4 of the Data Dictionary introduces alternative coordinates. An
    example of this can be found in the ``core_profiles`` IDS in
    ``profiles_1d(itime)/grid/rho_tor_norm``. Alternatives for this coordinate
    are:
    
    -   ``profiles_1d(itime)/grid/rho_tor``
    -   ``profiles_1d(itime)/grid/psi``
    -   ``profiles_1d(itime)/grid/volume``
    -   ``profiles_1d(itime)/grid/area``
    -   ``profiles_1d(itime)/grid/surface``
    -   ``profiles_1d(itime)/grid/rho_pol_norm``

    Multiple alternative coordinates may be filled (for example, an IDS might
    fill both the normalized and non-normalized toroidal flux coordinate). In
    that case, the size must be the same.

    When a quantity refers to this set of alternatives (for example
    ``profiles_1d(itime)/electrons/temperature``), at least one of the
    alternative coordinates must be set and its size must match the size of the
    quantity.

3.  The Data Dictionary can indicate exclusive alternative coordinates. See for
    example the ``distribution(i1)/profiles_2d(itime)/density(:,:)`` quantity in the
    ``distributions`` IDS, which has as first coordinate
    ``distribution(i1)/profiles_2d(itime)/grid/r OR
    distribution(i1)/profiles_2d(itime)/grid/rho_tor_norm``. This means that
    either ``r`` or ``rho_tor_norm`` can be used as coordinate.
    
    Validation works the same as explained in the previous point, except that
    exactly one of the alternative coordinate must be filled. Its size must, of
    course, still match the size of the data in the specified dimension.

4.  Some quantites indicate a coordinate must be the same size as another quantity
    through the property ``coordinateX_same_as``. In this case, the other quantity is
    not a coordinate, but their data is related and must be of the same size.

    An example can be found in the ``edge_profiles`` IDS, quantity
    ``ggd(itime)/neutral(i1)/velocity(i2)/diamagnetic``. This is a two-dimensional field
    for which the first coordinate must be the same as
    ``ggd(itime)/neutral(i1)/velocity(i2)/radial``. When the diamagnetic velocity
    component is filled, the radial component must be filled as well, and have a
    matching size.
