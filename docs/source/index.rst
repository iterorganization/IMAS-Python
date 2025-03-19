.. 
   Master "index". This will be converted to a landing index.html by sphinx. We
   define TOC here, but it'll be put in the sidebar by the theme

==================
IMAS-Python manual
==================

IMAS-Python is a pure-python library to handle arbitrarily nested
data structures. IMAS-Python is designed for, but not necessarily bound to,
interacting with Interface Data Structures (IDSs) as defined by the
Integrated Modelling & Analysis Suite (IMAS) Data Model.

.. note::

    IMAS-Python was formerly known as IMASPy, and was renamed with the release
    of the major version 2. 

It provides:

- An easy-to-install and easy-to-get started package by
  * Not requiring an IMAS installation
  * Not strictly requiring matching a Data Dictionary (DD) version
- A pythonic alternative to the IMAS Python High Level Interface (HLI)
- Checking of correctness at assign time, instead of at database write time
- Dynamically created in-memory pre-filled data trees from DD XML specifications

The README is best read on :src:`#imas`.

Read what's new in the current version of IMAS-Python in our :ref:`changelog`!


Manual
------

.. toctree::
   :caption: Getting Started
   :maxdepth: 1

   self
   installing
   intro
   multi-dd
   validation
   resampling
   metadata
   lazy_loading
   mdsplus
   identifiers
   configuring
   cli
   netcdf
   changelog

.. toctree::
   :caption: IMAS-Python training courses
   :maxdepth: 1

   courses/basic_user_training
   courses/advanced_user_training


.. toctree::
   :caption: API docs
   :maxdepth: 1

   api
   api-hidden


.. toctree::
   :caption: IMAS-Python development
   :maxdepth: 1

   imas_architecture
   code_style
   ci_config
   benchmarking
   release_imas


LICENSE
-------

.. literalinclude:: ../../LICENSE.txt
   :language: text
