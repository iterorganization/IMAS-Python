# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
import os

import imas

# Open input datafile
pulse, run, user, database = 134173, 106, "public", "ITER"
input = imas.DBEntry(imas.imasdef.MDSPLUS_BACKEND, database, pulse, run, user)
input.open()

# Read Te profile and the associated normalised toroidal flux coordinate
get_these_idss = ["equilibrium", "core_profiles"]
idss = {}
# The reference has 871 timepoints
for time_index in [0, 433, 871]:
    for ids_name in get_these_idss:
        if ids_name not in idss:
            idss[ids_name] = []
        idss[ids_name].append(
            input.get_slice(
                ids_name,
                time_index,
                imas.imasdef.PREVIOUS_INTERP,
                occurrence=0,
            )
        )

# Close the datafile
input.close()

# Dump the data to ASCII
# Create output datafile
temp = imas.DBEntry(imas.imasdef.MEMORY_BACKEND, database, pulse, run, user)
temp.create()
for ids_name, ids_list in idss.items():
    for ids_slice in ids_list:
        temp.put_slice(ids_slice)

uber_idss = {}
for ids_name in idss:
    uber_idss[ids_name] = temp.get(ids_name)
temp.close()


user = os.getenv("USER")
# Because we use the ASCII backend, this results in a .ids file in the cwd
output = imas.DBEntry(imas.imasdef.ASCII_BACKEND, database, pulse, run, user)
output.create()

# Save the IDS
for ids_name, ids in uber_idss.items():
    print(f"Putting {ids_name}")
    output.put(ids)

# Close the output datafile
output.close()
