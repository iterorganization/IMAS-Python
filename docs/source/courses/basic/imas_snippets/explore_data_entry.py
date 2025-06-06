import imas

# Open input data entry 
entry = imas.DBEntry("imas:hdf5?path=<...>", "r")

# Print the list of available IDSs with their occurrence
for idsname in imas.IDSFactory().ids_names():
    for occ in entry.list_all_occurrences(idsname):
        print(idsname, occ)

entry.close()
