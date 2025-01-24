import os

import matplotlib
# To avoid possible display issues when Matplotlib uses a non-GUI backend
if "DISPLAY" not in os.environ:
    matplotlib.use("agg")
else:
    matplotlib.use("TKagg")

import matplotlib.pyplot as plt
import numpy
import imas
import imas.training
import xarray

# 1. Load core_profiles IDS from training DBEntry
entry = imas.training.get_training_db_entry()
cp = entry.get("core_profiles")

# 2. Store the temperature of the first time slice
temperature = cp.profiles_1d[0].t_i_average

# Verify that the coordinates don't change
for p1d in cp.profiles_1d:
    assert numpy.allclose(p1d.t_i_average.coordinates[0], temperature.coordinates[0])

# 3. Get the required labels and data:
# Concatenate all temperature arrays:
data = numpy.array([p1d.t_i_average for p1d in cp.profiles_1d])
coordinates = {
    "time": cp.profiles_1d.coordinates[0],
    **{
        coordinate.metadata.name: coordinate
        for coordinate in temperature.coordinates
    }
}
attributes = {"units": temperature.metadata.units}
name = "t_i_average"

# 4. Create the DataArray
temperature = xarray.DataArray(data, coords=coordinates, attrs=attributes, name=name)
print(temperature)

# 5a. Select subset of temperature where 0.4 <= rho_tor_norm < 0.6:
print(temperature.sel(rho_tor_norm=slice(0.4, 0.6)))

# 5b. Interpolate temperature on a new grid: [0, 0.1, 0.2, ..., 0.9, 1.0]
print(temperature.interp(rho_tor_norm=numpy.linspace(0, 1, 11)))

# 5c. Interpolate temperature on a new time base: [10, 20]
print(temperature.interp(time=[10, 20]))

# 5d. Plot
temperature.plot(x="time", norm=matplotlib.colors.LogNorm())
plt.show()
