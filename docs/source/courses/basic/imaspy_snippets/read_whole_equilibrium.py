import imas.training

# Open input data entry
entry = imas.training.get_training_db_entry()

# 1. Read and print the time of the equilibrium IDS for the whole scenario
#    This explicitly converts the data from the old DD version on disk, to the
#    new DD version of the environment that you have loaded!
equilibrium = entry.get("equilibrium")  # All time slices
# 2. Print the time array:
print(equilibrium.time)

# 3. Load the core_profiles IDS
core_profiles = entry.get("core_profiles")
# 4. When you inspect the core_profiles.time array, you'll find that item [1]
#    corresponds to t ~ 433s.
# 5. Print the electron temperature
print(core_profiles.profiles_1d[1].electrons.temperature)

# Close input data entry
entry.close()
