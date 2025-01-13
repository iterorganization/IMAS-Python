import imas
import imas.training
from imas.util import get_full_path

# 1. Load the training data equilibrium IDS
entry = imas.training.get_training_db_entry()
equilibrium = entry.get("equilibrium")


# 2. Function that prints the path, shape and size of an IDS node
def print_path_shape_size(node):
    print(f"{get_full_path(node):40}: shape {node.shape} with total {node.size} items.")


# 3. Apply to equilibrium IDS
imas.util.visit_children(print_path_shape_size, equilibrium)
print()


# 4. Update function to skip 0D nodes
def print_path_shape_size_not0d(node):
    if node.metadata.ndim == 0:
        return
    print(f"{get_full_path(node):40}: shape {node.shape} with total {node.size} items.")


# And apply to the equilibrium IDS
imas.util.visit_children(print_path_shape_size_not0d, equilibrium)
