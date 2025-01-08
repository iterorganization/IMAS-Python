import datetime

import imas
import numpy as np


factory = imas.IDSFactory()
cp = factory.new("core_profiles")
# Alternative
cp = factory.core_profiles()

# Set properties
cp.ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS
cp.ids_properties.comment = "Synthetic IDS created for the imas-python course"
cp.ids_properties.creation_date = datetime.date.today().isoformat()

# Set a time array
cp.time = [1.0, 2.5, 4.0]

# Main coordinate
rho_tor_norm = np.linspace(0, 1, num=64)

# Generate some 1D profiles
cp.profiles_1d.resize(len(cp.time))
for index, t in enumerate(cp.time):
    t_e = np.exp(-16 * rho_tor_norm**2) + (1 - np.tanh(4 * rho_tor_norm - 3)) * t / 8
    t_e *= t * 500
    # Store the generated t_e as electron temperature
    cp.profiles_1d[index].electrons.temperature = t_e

# Validate the IDS for consistency
try:
    cp.validate()
    print("IDS is valid!")
except imas.exception.ValidationError as exc:
    print("Oops, the IDS is not valid: ", exc)

# Fill in the missing rho_tor_norm coordinate
for index in range(3):
    cp.profiles_1d[index].grid.rho_tor_norm = rho_tor_norm
# And validate again
cp.validate()

# Create a new data entry for storing the IDS
pulse, run, database = 1, 1, "imas-course"
entry = imas.DBEntry(imas.ids_defs.ASCII_BACKEND, database, pulse, run)
entry.create()

entry.put(cp)
