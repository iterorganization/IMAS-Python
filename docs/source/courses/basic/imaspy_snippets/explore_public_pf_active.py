import imas.util

# Open input data entry
entry = imas.DBEntry(
    imas.ids_defs.HDF5_BACKEND, "ITER_MD", 111001, 103, "public", data_version="3"
)
entry.open()

# Get the pf_active IDS
pf = entry.get("pf_active")

# Inspect the IDS
imas.util.inspect(pf, hide_empty_nodes=True)

entry.close()
