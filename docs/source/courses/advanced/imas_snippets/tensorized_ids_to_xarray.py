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

#######################################################################################
# Steps 2, 3 and 4, using imas.util.to_xarray
# Create an xarray Dataset containing t_i_average and its coordinates
xrds = imas.util.to_xarray(cp, "profiles_1d/t_i_average")
# Note that profiles_1d.grid.rho_tor_norm is a 2D coordinate: its values may be
# different at different times.
#
# Since the values at different time slices differ only minutely in this example, we'll
# rename the `profiles_1d.grid.rho_tor_norm:i` dimension to `rho_tor_norm` and set the
# values to the values of rho_tor_norm of the first time slice:
xrds = xrds.rename({"profiles_1d.grid.rho_tor_norm:i": "rho_tor_norm"}).assign_coords(
    {"rho_tor_norm": xrds["profiles_1d.grid.rho_tor_norm"].isel(time=0).data}
)

# Extract temperatures as an xarray DataArray
temperature = xrds["profiles_1d.t_i_average"]

# 5a. Select subset of temperature where 0.4 <= rho_tor_norm < 0.6:
print(temperature.sel(rho_tor_norm=slice(0.4, 0.6)))

# 5b. Interpolate temperature on a new grid: [0, 0.1, 0.2, ..., 0.9, 1.0]
print(temperature.interp(rho_tor_norm=numpy.linspace(0, 1, 11)))

# 5c. Interpolate temperature on a new time base: [10, 20]
print(temperature.interp(time=[10, 20]))

# 5d. Plot
temperature.plot(x="time", norm=matplotlib.colors.LogNorm())
plt.show()

#######################################################################################
# We can also manually build an xarray DataArray, this is shown below:

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
