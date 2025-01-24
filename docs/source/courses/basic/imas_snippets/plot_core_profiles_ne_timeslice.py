import os

import matplotlib
import imas.training

# To avoid possible display issues when Matplotlib uses a non-GUI backend
if "DISPLAY" not in os.environ:
    matplotlib.use("agg")
else:
    matplotlib.use("TKagg")

import matplotlib.pyplot as plt

# Open input data entry
entry = imas.training.get_training_db_entry()

# Read n_e profile and the associated normalised toroidal flux coordinate at
t = 443  # seconds

cp = entry.get_slice("core_profiles", t, imas.ids_defs.CLOSEST_INTERP)

# profiles_1d should only contain the requested slice
assert len(cp.profiles_1d) == 1

ne = cp.profiles_1d[0].electrons.density
rho = cp.profiles_1d[0].grid.rho_tor_norm

# Plot the figure
fig, ax = plt.subplots()
ax.plot(rho, ne)
ax.set_ylabel(r"$n_e$")
ax.set_xlabel(r"$\rho_{tor, norm}$")
ax.ticklabel_format(axis="y", scilimits=(-1, 1))
plt.show()
