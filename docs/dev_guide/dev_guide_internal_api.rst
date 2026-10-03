==================
Internal Reference
==================

This reference covers the whole :mod:`vicar` package, including the private methods
and attributes of :class:`~vicar.VicarLabel` and :class:`~vicar.VicarImage` and the
two private modules that hold the VICAR definitions and the label grammar. Public
members link to their entries in the :doc:`public API reference <../module>`.

``vicar`` Package
=================

.. automodule:: vicar
    :no-index:
    :member-order: groupwise
    :members:
    :undoc-members:
    :special-members:
    :private-members:
    :exclude-members: __dict__, __hash__, __module__, __weakref__, __annotations__, __abstractmethods__
    :show-inheritance:

Formatting-Hint Types
=====================

The private methods of :class:`~vicar.VicarLabel` record the formatting hints of each
parameter value in these named tuples, defined in ``vicar/vicarlabel.py``.

.. autoclass:: vicar.vicarlabel._ValueFormat
    :members:

.. autoclass:: vicar.vicarlabel._ListFormat
    :members:

``vicar._DEFINITIONS`` Module
=============================

.. automodule:: vicar._DEFINITIONS
    :members:
    :undoc-members:
    :private-members:

``vicar._LABEL_GRAMMAR`` Module
===============================

.. automodule:: vicar._LABEL_GRAMMAR
    :members:
    :undoc-members:
    :private-members:
