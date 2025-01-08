import imas
import imas.training

# Open input data entry
entry = imas.training.get_training_imas_db_entry()

cp = entry.get("core_profiles")
for el in ["profiles_1d", "global_quantities", "code"]:
    try:
        print(getattr(cp, el))
    except NameError:
        print(f"Could not print {el}, internal IMAS error")
