# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Functions that are useful for the imas-python training courses.
"""

import importlib
from unittest.mock import patch

try:
    from importlib.resources import files
except ImportError:  # Python 3.8 support
    from importlib_resources import files

import imas
from imas.backends.imas_core.imas_interface import ll_interface


def _initialize_training_db(DBEntry_cls):
    assets_path = files(imas) / "assets/"
    pulse, run, user, database = 134173, 106, "public", "ITER"
    if ll_interface._al_version.major == 4:
        entry = DBEntry_cls(imas.ids_defs.ASCII_BACKEND, database, pulse, run, user)
        entry.open(options=f"-prefix {assets_path}/")
    else:
        entry = DBEntry_cls(f"imas:ascii?path={assets_path}", "r")

    output_entry = DBEntry_cls(imas.ids_defs.MEMORY_BACKEND, database, pulse, run)
    output_entry.create()
    for ids_name in ["core_profiles", "equilibrium"]:
        ids = entry.get(ids_name)
        with patch.dict("os.environ", {"IMAS_AL_DISABLE_VALIDATE": "1"}):
            output_entry.put(ids)
    entry.close()
    return output_entry


def get_training_db_entry() -> imas.DBEntry:
    """Open and return an ``imas.DBEntry`` pointing to the training data."""
    return _initialize_training_db(imas.DBEntry)


def get_training_imas_db_entry():
    """Open and return an ``imas.DBEntry`` pointing to the training data."""
    imas = importlib.import_module("imas")
    return _initialize_training_db(imas.DBEntry)
