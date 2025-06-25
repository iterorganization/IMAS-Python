Custom conversion of the ``em_coupling`` IDS
============================================

The ``em_coupling`` IDS has had a big change between Data Dictionary 3.x and Data
Dictionary 4.x. These changes are not covered by the automatic conversions of
:py:meth:`imas.convert_ids <imas.ids_convert.convert_ids>` because these are too
code-specific.

Instead we show on this page an example to convert a DINA dataset from DD 3.38.1 to DD
4.0.0, which can be used as a starting point for converting output data from other codes
as well.

.. literalinclude:: custom_conversion_em_coupling.py
