# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""Load IMAS-Python libs to provide constants

.. _`Backend identifiers`:

Backend identifiers
-------------------

The following constants are identifiers for the different Access Layer backends. Please
see the Access Layer documentation for more details on the different backends.

.. data:: ASCII_BACKEND

    Identifier for the ASCII backend.

.. data:: MDSPLUS_BACKEND

    Identifier for the MDS+ backend.

.. data:: HDF5_BACKEND

    Identifier for the HDF5 backend.

.. data:: MEMORY_BACKEND

    Identifier for the memory backend.

.. data:: UDA_BACKEND

    Identifier for the UDA backend.


Time modes
----------

.. data:: IDS_TIME_MODE_HOMOGENEOUS

    Use homogeneous time, all time coordinates refer to the toplevel ``time`` array.

.. data:: IDS_TIME_MODE_HETEROGENEOUS

    Use heterogeneous time, time coordinates refer to their local ``time`` array.

.. data:: IDS_TIME_MODE_INDEPENDENT

    Indicates that this IDS does not store time-dependent data.


Interpolation modes
-------------------

.. data:: CLOSEST_INTERP

    Interpolation method that returns the `closest` time slice in the original IDS (can
    break causality as it can return data ahead of requested time).

.. data:: PREVIOUS_INTERP

    Interpolation method that returns the `previous` time slice if the requested time
    does not exactly exist in the original IDS.

.. data:: LINEAR_INTERP

    Interpolation method that returns a linear interpolation between the existing slices
    before and after the requested time.


Serializer protocols
--------------------

.. data:: ASCII_SERIALIZER_PROTOCOL

    Identifier for the ASCII serialization protocol.

.. data:: FLEXBUFFERS_SERIALIZER_PROTOCOL

    Identifier for the Flexbuffers serialization protocol. This protocol is more
    performant and results in a smaller buffer size than the
    :data:`ASCII_SERIALIZER_PROTOCOL`.

    .. versionadded:: 1.1 Requires ``imas_core`` version 5.3 or newer.

.. data:: DEFAULT_SERIALIZER_PROTOCOL

    Identifier for the default serialization protocol.
"""

import logging

from imas.backends.imas_core.imas_interface import imasdef

logger = logging.getLogger(__name__)


ASCII_BACKEND = imasdef.ASCII_BACKEND
CHAR_DATA = imasdef.CHAR_DATA
CLOSE_PULSE = imasdef.CLOSE_PULSE
CLOSEST_INTERP = imasdef.CLOSEST_INTERP
CREATE_PULSE = imasdef.CREATE_PULSE
DOUBLE_DATA = imasdef.DOUBLE_DATA
COMPLEX_DATA = imasdef.COMPLEX_DATA
EMPTY_COMPLEX = imasdef.EMPTY_COMPLEX
EMPTY_FLOAT = imasdef.EMPTY_FLOAT
EMPTY_INT = imasdef.EMPTY_INT
ERASE_PULSE = imasdef.ERASE_PULSE
FORCE_CREATE_PULSE = imasdef.FORCE_CREATE_PULSE
FORCE_OPEN_PULSE = imasdef.FORCE_OPEN_PULSE
HDF5_BACKEND = imasdef.HDF5_BACKEND
IDS_TIME_MODE_HETEROGENEOUS = imasdef.IDS_TIME_MODE_HETEROGENEOUS
IDS_TIME_MODE_HOMOGENEOUS = imasdef.IDS_TIME_MODE_HOMOGENEOUS
IDS_TIME_MODE_INDEPENDENT = imasdef.IDS_TIME_MODE_INDEPENDENT
IDS_TIME_MODE_UNKNOWN = imasdef.IDS_TIME_MODE_UNKNOWN
IDS_TIME_MODES = imasdef.IDS_TIME_MODES
INTEGER_DATA = imasdef.INTEGER_DATA
LINEAR_INTERP = imasdef.LINEAR_INTERP
MDSPLUS_BACKEND = imasdef.MDSPLUS_BACKEND
MEMORY_BACKEND = imasdef.MEMORY_BACKEND
NODE_TYPE_STRUCTURE = imasdef.NODE_TYPE_STRUCTURE
OPEN_PULSE = imasdef.OPEN_PULSE
PREVIOUS_INTERP = imasdef.PREVIOUS_INTERP
READ_OP = imasdef.READ_OP
UDA_BACKEND = imasdef.UDA_BACKEND
UNDEFINED_INTERP = imasdef.UNDEFINED_INTERP
UNDEFINED_TIME = imasdef.UNDEFINED_TIME
WRITE_OP = imasdef.WRITE_OP
ASCII_SERIALIZER_PROTOCOL = getattr(imasdef, "ASCII_SERIALIZER_PROTOCOL", 60)
FLEXBUFFERS_SERIALIZER_PROTOCOL = getattr(
    imasdef, "FLEXBUFFERS_SERIALIZER_PROTOCOL", None
)
DEFAULT_SERIALIZER_PROTOCOL = getattr(imasdef, "DEFAULT_SERIALIZER_PROTOCOL", 60)
