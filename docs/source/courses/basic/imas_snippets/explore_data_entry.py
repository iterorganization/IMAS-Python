import imas

# Open input data entry
entry = imas.DBEntry("imas:hdf5?path=<...>","r")

# Print the list of available IDSs with their occurrence
print([(idsname,occ) for idsname in imas.IDSFactory().ids_names() for occ in entry.list_all_occurrences(idsname)])

entry.close()
