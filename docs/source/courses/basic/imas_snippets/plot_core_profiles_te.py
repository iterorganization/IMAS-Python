import os

import matplotlib
import numpy

# To avoid possible display issues when Matplotlib uses a non-GUI backend
if "DISPLAY" not in os.environ:
    matplotlib.use("agg")
else:
    matplotlib.use("TKagg")

from matplotlib import pyplot as plt

import imas
from imas.ids_defs import MDSPLUS_BACKEND

database, pulse, run, user = "ITER", 134173, 106, "public"
data_entry = imas.DBEntry(
    MDSPLUS_BACKEND, database, pulse, run, user, data_version="3"
)
data_entry.open()
# Enable lazy loading with `lazy=True`:
core_profiles = data_entry.get("core_profiles", lazy=True)

# No data has been read from the lowlevel backend yet
# The time array is loaded only when we access it on the following lines:
time = core_profiles.time
print(f"Time has {len(time)} elements, between {time[0]} and {time[-1]}")

# Find the electron temperature at rho=0 for all time slices
electon_temperature_0 = numpy.array(
    [p1d.electrons.temperature[0] for p1d in core_profiles.profiles_1d]
)

# Plot the figure
fig, ax = plt.subplots()
ax.plot(time, electon_temperature_0)
ax.set_ylabel("$T_e$")
ax.set_xlabel("$t$")
plt.show()
