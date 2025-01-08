import imas.training

# Open input data entry
entry = imas.training.get_training_db_entry()

# Read n_e profile and the associated normalised toroidal flux coordinate at
t = 443  # seconds

cp = entry.get_slice("core_profiles", t, imas.ids_defs.CLOSEST_INTERP)

# profiles_1d should only contain the requested slice
assert len(cp.profiles_1d) == 1

ne = cp.profiles_1d[0].electrons.density
rho = cp.profiles_1d[0].grid.rho_tor_norm
print("ne =", ne)
print("rho =", rho)

# Close the datafile
entry.close()
