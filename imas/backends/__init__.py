# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Logic for interacting with all data backends.

Currently supported backends are:

-   ``imas_core``: IMAS Access Layer Core (lowlevel).

    Interfaces with the AL core provided by Python package ``imas_core`` (available
    since AL5.2). For older versions it falls back to the ``imas`` HLI module, which
    contains the interface to ``imas_core``.
"""
