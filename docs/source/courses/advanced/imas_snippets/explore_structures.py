import imas
import imas.training

# 1. Load the equilibrium IDS from the training data
entry = imas.training.get_training_db_entry()
equilibrium = entry.get("equilibrium")

# 2. Print non-empty child nodes
print("The following child nodes of the equilibrium IDS are filled:")
for child_node in equilibrium.iter_nonempty_():
    print('-', child_node.metadata.name)
print()

# 3. Print child nodes of ids_properties
print("equilibrium/ids_properties has the following child nodes:")
for child_node in equilibrium.ids_properties:
    print(f"- {child_node.metadata.name}: {child_node!r}")
