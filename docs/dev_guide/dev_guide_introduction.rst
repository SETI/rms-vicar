============
Introduction
============

Who This Guide Is For
=====================

This guide is for anyone who changes ``rms-vicar``: fixing a bug, adding a method,
supporting another data type, or cutting a release. It assumes a competent Python
developer who is fluent with NumPy and pytest but new to this code base and to the VICAR
format. The README and the :doc:`public API reference </module>` explain how to use the
package. This guide is about the source, and it concentrates on the invariants that hold
the package together rather than restating what the code says.

Package Overview
================

``rms-vicar``, imported as :mod:`vicar`, reads and writes files in VICAR, the image
format of the Video Image Communication and Retrieval system developed at NASA's Jet
Propulsion Laboratory. A VICAR file is a text label followed by binary data. The label is
a sequence of ``NAME=VALUE`` parameters. Some parameters describe the layout of the
binary data that follows, and the rest are free-form metadata, often repeated once for
each processing step the file has been through. The authoritative description of the
format is the `VICAR File Format
<https://pds-rings.seti.org/help/VICAR_file_fmt.pdf>`_ document.

The package has three public classes:

* :class:`~vicar.VicarLabel` holds a label as an ordered list of parameters. It parses
  label text, supports dictionary-like access with a rich key syntax, preserves the
  spacing and number formats of the original text, and exports the label back to text.
* :class:`~vicar.VicarImage` combines a :class:`~vicar.VicarLabel` with the binary
  content of a file: the data array, the optional prefix bytes at the start of each
  record, and the optional binary header. It reads and writes complete files and keeps
  the structural label parameters consistent with the arrays it holds.
* :class:`~vicar.VicarError` is the exception raised when a label or file violates the
  VICAR standard.

Runtime requirements are Python 3.11 or later, NumPy, ``pyparsing`` for the label
grammar, ``rms-filecache`` for reading and writing local and remote files through
:class:`~filecache.file_cache_path.FCPath`, and ``rms-vax`` for converting VAX
floating-point data in older files. The package runs on Linux, macOS, and Windows, and
the test matrix covers all three.

Development requirements are declared as extras in ``pyproject.toml``. The ``dev`` extra
brings the linters, the test tools, the packaging check, and the type checker whose
stubtest subcommand validates the type stub; it also pulls in the ``docs`` extra, which
brings Sphinx and its extensions.

Where to Look
=============

* :doc:`/module` is the public API reference, generated from the docstrings.
* :doc:`dev_guide_internal_api` is a second copy of the API reference that includes the
  private methods and the two private modules, generated from the same docstrings.
* :doc:`/contributing` is the contribution guide.
* ``CLAUDE.md`` and the files under ``.claude/rules/`` in the repository root are the
  detailed working rules, written for AI-assisted development but binding on everyone.
  :doc:`dev_guide_conventions` summarizes them.
