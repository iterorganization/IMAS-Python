import logging
import uuid
from pathlib import Path

import imas
import imas.exception
import imas.ids_defs

# Backend constants
HDF5 = "HDF5"
MDSPLUS = "MDSplus"
MEMORY = "memory"
ASCII = "ASCII"
NETCDF = "netCDF"


def create_uri(backend, path):
    if backend == NETCDF:
        return f"{path}.nc"
    return f"imas:{backend.lower()}?path={path}"


def backend_exists(backend):
    """Tries to detect if the lowlevel has support for the given backend."""
    uri = create_uri(backend, str(uuid.uuid4()))
    try:
        entry = imas.DBEntry(uri, "r")
    except Exception as exc:
        if "backend is not available" in str(exc):
            return False
        elif isinstance(exc, (imas.exception.ALException, FileNotFoundError)):
            return True
        return True
    # Highly unlikely, but it could succeed without error
    entry.close()
    return True


# Note: UDA backend is not used for benchmarking
all_backends = [
    HDF5,
    MDSPLUS,
    MEMORY,
    ASCII,
    NETCDF,
]

# Suppress error logs for testing backend availabitily:
#   ERROR:root:b'ual_open_pulse: [UALBackendException = HDF5 master file not found: <path>]'
#   ERROR:root:b'ual_open_pulse: [UALBackendException = %TREE-E-FOPENR, Error opening file read-only.]'
#   ERROR:root:b'ual_open_pulse: [UALBackendException = Missing pulse]'
logging.getLogger().setLevel(logging.CRITICAL)
available_backends = list(filter(backend_exists, all_backends))
logging.getLogger().setLevel(logging.INFO)
available_slicing_backends = [
    backend for backend in available_backends if backend not in [ASCII, NETCDF]
]

available_serializers = [
    imas.ids_defs.ASCII_SERIALIZER_PROTOCOL,
    imas.ids_defs.FLEXBUFFERS_SERIALIZER_PROTOCOL,
]


def create_dbentry(backend):
    path = Path.cwd() / f"DB-{backend}"
    return imas.DBEntry(create_uri(backend, path), "w")
