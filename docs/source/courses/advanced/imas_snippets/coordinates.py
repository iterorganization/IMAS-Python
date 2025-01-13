import imas.training

# 1. Load the training data for the core_profiles IDS:
entry = imas.training.get_training_db_entry()
core_profiles = entry.get("core_profiles")

# 1a. Print the coordinate of profiles_1d[0].electrons.temperature
print(core_profiles.profiles_1d[0].electrons.temperature.coordinates[0])
# Do you recognize the coordinate? Yes, as shown in the first line of the output, this
# is "profiles_1d[0]/grid/rho_tor_norm".

# 1b. Print the coordinate of profiles_1d:
print(core_profiles.profiles_1d.coordinates[0])
# What do you notice? This prints the core_profiles.time array:
#   <IDSNumericArray (IDS:core_profiles, time, FLT_1D)>
#   numpy.ndarray([  3.98722186, 432.93759781, 792.        ])

# 1c. Change the time mode and print again
core_profiles.ids_properties.homogeneous_time = \
    imas.ids_defs.IDS_TIME_MODE_HETEROGENEOUS
print(core_profiles.profiles_1d.coordinates[0])
# What has changed? Now we get a numpy array with values -9e+40:
#   [-9.e+40 -9.e+40 -9.e+40]
#
# In heterogeneous time, the coordinate of profiles_1d is profiles_1d/time, which is a
# scalar. imas-python will construct a numpy array for you where
#   array[i] := profiles_1d[i]/time
# Since we didn't set these values, they are set to the default EMPTY_FLOAT, which is
# -9e+40.

# 2. Load the training data for the equilibrium IDS:
equilibrium = entry.get("equilibrium")

# 2a. What is the coordinate of time_slice/profiles_2d?
slice0 = equilibrium.time_slice[0]
print(slice0.profiles_2d.metadata.coordinates)
# This will output:
#   (IDSCoordinate('1...N'),)
# The coordinate of profiles_2d is an index. When requesting the coordinate values,
# imas-python will generate an index array for you:
print(slice0.profiles_2d.coordinates[0])
# -> array([0])

# 2b. What are the coordinates of ``time_slice/profiles_2d/b_field_r``?
print(slice0.profiles_2d[0].b_field_r.metadata.coordinates)
# This is a 2D array and therefore there are two coordinates:
#   (IDSCoordinate('time_slice(itime)/profiles_2d(i1)/grid/dim1'),
#    IDSCoordinate('time_slice(itime)/profiles_2d(i1)/grid/dim2'))
