import imas.util
import imas.training

# Open input data entry
entry = imas.training.get_training_db_entry()

# Get the core_profiles IDS
cp = entry.get("core_profiles")

# Inspect the IDS
imas.util.inspect(cp, hide_empty_nodes=True)

entry.close()