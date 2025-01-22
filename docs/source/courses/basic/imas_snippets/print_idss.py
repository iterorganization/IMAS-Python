import imas

# imas-python has multiple DD versions inside, which makes this exercise harder.
# We provide possible solutions here

# Option 1: Print the IDSs in the default-selected DD version
factory = imas.IDSFactory()
print("IDSs available in DD version", factory.version)
print(factory.ids_names())

# Alternative:
for ids_name in factory:
    print(ids_name, end=", ")
print()

# Option 2: Print the IDSs in a specific DD version
factory = imas.IDSFactory("3.39.0")
print("IDSs available in DD version", factory.version)
print(list(factory))
