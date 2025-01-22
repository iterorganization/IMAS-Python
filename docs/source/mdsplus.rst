.. _`MDSplus in imas-python`:

MDSplus in imas-python
======================

`MDSplus <https://www.mdsplus.org>`_ is a set of software tools for data
acquisition and storage and a methodology for management of complex
scientific data. imas-python uses the IMAS LowLevel interface to interact
with MDSplus data. The model files required to read IMAS IDS-structured
data are generated on demand, whenever a specific DD version is used
by the user. As this generation might take a while, MDSplus models are
cached to disk, generally in ``$HOME/.cache/imas``. As multiple
processes can write to this location, especially during testing,
special care is taken to avoid write collisions.
``$MDSPLUS_MODEL_TIMEOUT`` can be used to specify the amount of seconds
to wait in case the default is not sufficient.
