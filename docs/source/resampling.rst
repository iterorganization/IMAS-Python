Resampling
==========

For resampling of data we stick close to the numpy and scipy APIs. The relevant
method signatures are reproduced here:

.. code-block:: python

    Class scipy.interpolate.interp1d(x, y, kind='linear', axis=- 1, copy=True,
        bounds_error=None, fill_value=nan, assume_sorted=False)

Which produces a resampling function, whose call method uses interpolation to
find the value of new points. This can be used like so:

.. code-block:: python

    pulse_schedule = imas.IDSFactory().new("pulse_schedule")
    f = scipy.interpolate.interp1d(pulse_schedule.time, pulse_schedule_some_1d_var)
    ids.pulse_schedule.some_1d_var = f(pulse_schedule.some_1d_var)


A more general approach would work on the basis of scanning the tree for
shared coordinates, and resampling those in the same manner (by creating a
local interpolator and applying it). The :py:meth:`imas.util.visit_children`
method can
be used for this. For a proof-of-concept it is recommended to only resample
in the time direction.

For example, a proposal implementation included in 0.4.0 can be used as such
(inplace interpolation on an IDS leaf node)

.. code-block:: python

    import imas
    nbi = imas.IDSFactory().new("nbi")
    nbi.ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS
    nbi.time = [1, 2, 3]
    nbi.unit.resize(1)
    nbi.unit[0].energy.data = 2 * nbi.time
    old_id = id(nbi.unit[0].energy.data)

    imas.util.resample(
        nbi.unit[0].energy.data,
        nbi.time,
        [0.5, 1.5],
        nbi.ids_properties.homogeneous_time,
        inplace=True,
        fill_value="extrapolate",
    )

    assert old_id == id(nbi.unit[0].energy.data)
    assert list(nbi.unit[0].energy.data) == [1, 3]


Or as such (explicit in-memory copy + interpolation, producing a new data leaf/container):

.. code-block:: python

    nbi = imas.IDSFactory().new("nbi")
    nbi.ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS
    nbi.time = [1, 2, 3]
    nbi.unit.resize(1)
    nbi.unit[0].energy.data = 2 * nbi.time
    old_id = id(nbi.unit[0].energy.data)

    new_data = imas.util.resample(
        nbi.unit[0].energy.data,
        nbi.time,
        [0.5, 1.5],
        nbi.ids_properties.homogeneous_time,
        inplace=False,
        fill_value="extrapolate",
    )

    assert old_id != id(new_data)
    assert list(new_data) == [1, 3]


Implementation unit tests can be found in `test_latest_dd_resample.py`.


Alternative resampling methods
------------------------------

.. code-block:: python

    scipy.signal.resample(x, num, t=None, axis=0, window=None, domain='time')

`Scipy.signal.resample` uses a Fourier method to resample, which assumes the
signal is periodic. It can be very slow if the number of input or output
samples is large and prime. See
https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample.html
for more information.

.. code-block:: python

    scipy.signal.resample_poly(x, up, down, axis=0, window='kaiser', 5.0, padtype='constant', cval=None)

Could be considered, which uses a low-pass FIR filter. This assumes zero
values outside the boundary. See
https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html#scipy.signal.resample_poly
for more information.  We do not recommend to use simpler sampling methods
such as nearest-neighbour if possible, as this reduces the data quality and
does not result in a much simpler or faster implementation if care is taken.
