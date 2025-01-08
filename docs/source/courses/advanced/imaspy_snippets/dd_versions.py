import imas
from imas.util import get_data_dictionary_version

# 1. Create an IDSFactory
default_factory = imas.IDSFactory()

# 2. Print the DD version used by the IDSFactory
#
# This factory will use the default DD version, because we didn't explicitly indicate
# which version of the DD we want to use:
print("Default DD version:", default_factory.version)

# 3. Create an empty IDS
pf_active = default_factory.new("pf_active")
print("DD version used for pf_active:", get_data_dictionary_version(pf_active))
# What do you notice? This is the same version as the IDSFactory that was used to create
# it.

# 4. Create a new DBEntry
default_entry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "test", 0, 0)
default_entry.create()
# Alternative URI syntax when using AL5.0.0:
# default_entry = imas.DBEntry("imas:memory?path=.")
print("DD version used for the DBEntry:", get_data_dictionary_version(default_entry))
# What do you notice? It is the same default version again.
