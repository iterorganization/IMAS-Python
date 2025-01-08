import os

import imas
import imas.training
import matplotlib
import numpy as np
from scipy.interpolate import RegularGridInterpolator

if "DISPLAY" not in os.environ:
    matplotlib.use("agg")
else:
    matplotlib.use("TKagg")

import matplotlib.pyplot as plt

# Open input data entry
entry = imas.training.get_training_imas_db_entry()

# Use a partial get to retrieve the full time vector
input_times = entry.partial_get("equilibrium", "time")

# Create output data entry
output_entry = imas.DBEntry(
    imas.imasdef.MEMORY_BACKEND, "imas-course", 2, 1)
output_entry.create()

# Loop over each time slice
for time in input_times:
    eq = entry.get_slice("equilibrium", time, imas.imasdef.CLOSEST_INTERP)

    # Update comment
    eq.ids_properties.comment = "imas-python training: transform coordinate system"

    p2d = eq.time_slice[0].profiles_2d[0]
    r, z = p2d.grid.dim1, p2d.grid.dim2
    r_axis = eq.time_slice[0].global_quantities.magnetic_axis.r
    z_axis = eq.time_slice[0].global_quantities.magnetic_axis.z

    # Create new rho/theta coordinates
    theta = np.linspace(-np.pi, np.pi, num=64, endpoint=False)
    max_rho = min(
        r_axis - r[0],
        r[-1] - r_axis,
        z_axis - z[0],
        z[-1] - z_axis,
    )
    rho = np.linspace(0, max_rho, num=64)

    # Calculate corresponding R/Z for interpolating the original values
    rho_grid, theta_grid = np.meshgrid(rho, theta, indexing="ij", sparse=True)
    grid_r = r_axis + rho_grid * np.cos(theta_grid)
    grid_z = z_axis + rho_grid * np.sin(theta_grid)
    interpolation_points = np.dstack((grid_r.flatten(), grid_z.flatten()))

    # Interpolate all data nodes on the new grid
    for data_node in ["b_field_r", "b_field_z", "b_field_tor", "psi"]:
        data = getattr(p2d, data_node)
        interp = RegularGridInterpolator((r, z), data)
        new_data = interp(interpolation_points).reshape(grid_r.shape)
        setattr(p2d, data_node, new_data)

    # Update coordinate identifier
    p2d.grid_type.index = 2
    p2d.grid_type.name = "inverse"
    p2d.grid_type.description = "Rhopolar_polar 2D polar coordinates (rho=dim1, theta=dim2) with magnetic axis as centre of grid; theta and values following the COCOS=11 convention; the polar angle is theta=atan2(z-zaxis,r-raxis)"  # noqa: E501

    # Update coordinates
    p2d.grid.dim1 = rho
    p2d.grid.dim2 = theta
    p2d.r = grid_r
    p2d.z = grid_z

    # Finally, put the slice to disk
    output_entry.put_slice(eq)

# Create a plot to verify the transformation is correct
fig, (ax1, ax2, ax3) = plt.subplots(1, 3)

vmin, vmax = np.min(data), np.max(data)
contour_levels = np.linspace(vmin, vmax, 32)

rzmesh = np.meshgrid(r, z, indexing="ij")
mesh = ax1.pcolormesh(*rzmesh, data, vmin=vmin, vmax=vmax)
ax1.contour(*rzmesh, data, contour_levels, colors='black')

ax2.pcolormesh(grid_r, grid_z, new_data, vmin=vmin, vmax=vmax)
ax2.contour(grid_r, grid_z, new_data, contour_levels, colors='black')

rho_theta_mesh = np.meshgrid(rho, theta, indexing="ij")
ax3.pcolormesh(*rho_theta_mesh, new_data, vmin=vmin, vmax=vmax)
ax3.contour(*rho_theta_mesh, new_data, contour_levels, colors='black')

ax1.set_xlabel("r [m]")
ax2.set_xlabel("r [m]")
ax1.set_ylabel("z [m]")
ax2.set_xlim(ax1.get_xlim())
ax2.set_ylim(ax1.get_ylim())
ax3.set_xlabel(r"$\rho$ [m]")
ax3.set_ylabel(r"$\theta$ [rad]")

fig.suptitle(r"$\psi$ in ($r,z$) and ($\rho,\theta$) coordinates.")
fig.colorbar(mesh, ax=ax3)
fig.tight_layout()

plt.show()
