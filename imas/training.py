# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Functions that are useful for the IMAS-Python training courses."""

from unittest.mock import patch

try:
    from importlib.resources import files
except ImportError:  # Python 3.8 support
    from importlib_resources import files

import imas


def get_training_db_entry() -> imas.DBEntry:
    """Open and return an ``imas.DBEntry`` pointing to the training data."""
    assets_path = files(imas) / "assets/"
    entry = imas.DBEntry(f"imas:ascii?path={assets_path}", "r")

    output_entry = imas.DBEntry("imas:memory?path=/", "w")
    for ids_name in ["core_profiles", "equilibrium"]:
        ids = entry.get(ids_name, autoconvert=False)
        with patch.dict("os.environ", {"IMAS_AL_DISABLE_VALIDATE": "1"}):
            output_entry.put(imas.convert_ids(ids, output_entry.dd_version))
    entry.close()
    return output_entry
