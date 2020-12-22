# This file is part of IMASPy.
# You should have received IMASPy LICENSE file with this project.
""" Load IMASPy libs to provide constants
"""

import logging

from imaspy.logger import logger

logger.setLevel(logging.INFO)

try:
    import imas.hli_utils as hli_utils
    from imas.imasdef import (
        ASCII_BACKEND,
        CHAR_DATA,
        CLOSE_PULSE,
        DOUBLE_DATA,
        EMPTY_FLOAT,
        EMPTY_INT,
        FORCE_CREATE_PULSE,
        HDF5_BACKEND,
        IDS_TIME_MODE_HETEROGENEOUS,
        IDS_TIME_MODE_HOMOGENEOUS,
        IDS_TIME_MODE_INDEPENDENT,
        IDS_TIME_MODE_UNKNOWN,
        IDS_TIME_MODES,
        INTEGER_DATA,
        MDSPLUS_BACKEND,
        MEMORY_BACKEND,
        NODE_TYPE_STRUCTURE,
        OPEN_PULSE,
        READ_OP,
        UDA_BACKEND,
        WRITE_OP,
    )
except ImportError as ee:
    logger.critical("IMAS could not be imported. UAL not available! %s", ee)
else:
    # Translation dictionary to go from an ids (primitive) type (without the dimensionality) to a default value
    ids_type_to_default = {
        "STR": "",
        "INT": EMPTY_INT,
        "FLT": EMPTY_FLOAT,
    }
