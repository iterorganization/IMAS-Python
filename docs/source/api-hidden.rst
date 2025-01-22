.. Generate API reference pages, but don't display these in tables.
.. This extra page is a work around for sphinx not having any support for
.. hiding an autosummary table.

API autosummary
===============

.. Explicitly list submodules here
.. autosummary::
   :toctree: generated/
   :recursive:
   :template: custom-module-template.rst

   imas
