=========
The Image
=========

This chapter covers :class:`~vicar.VicarImage`, in ``src/vicar/vicarimage.py``.
:doc:`dev_guide_architecture` gives its place in the package and the steps of reading
and writing a file; this chapter covers the rules its methods keep.

File Layout
===========

A VICAR file is a sequence of fixed-length records of ``RECSIZE`` bytes, after a label
of ``LBLSIZE`` bytes, itself a whole number of records:

::

    LBLSIZE bytes          the label text, padded with null characters
    NLB records            the binary header, if any
    N2 * N3 records        the data, each record NBB prefix bytes then the image bytes
    rest of file           the EOL label, if EOL=1

:class:`~vicar.VicarImage` stores each part separately: the label as a
:class:`~vicar.VicarLabel`, the binary header as :class:`bytes` or a NumPy array, and the
data and prefix as three-dimensional NumPy arrays of shape ``(N3, N2, N1)`` and
``(N3, N2, NBB / itemsize)``. Two-dimensional arrays are accepted and stored with a
leading axis of length one; :attr:`~vicar.VicarImage.array2d` and
:attr:`~vicar.VicarImage.prefix2d` return them without it.

The Structural Parameters
=========================

The setters of :attr:`~vicar.VicarImage.array`, :attr:`~vicar.VicarImage.prefix`, and
:attr:`~vicar.VicarImage.binheader` each validate the new value against the other two
and then update the label:

* :attr:`~vicar.VicarImage.array` sets ``FORMAT`` from the dtype, ``INTFMT`` or
  ``REALFMT`` from its byte order, the dimensions from its shape, and ``RECSIZE`` from
  the record width, and recomputes ``NLB`` from the binary header's length.
* :attr:`~vicar.VicarImage.prefix` sets ``NBB`` and ``RECSIZE``, and sets ``FORMAT`` and
  the byte-order parameters only where the data array does not already determine them.
* :attr:`~vicar.VicarImage.binheader` sets ``NLB``, ``BHOST``, and, for an array,
  ``BINTFMT`` or ``BREALFMT``.

Each setter raises :class:`~vicar.VicarError`, and leaves the object unchanged, when the
new value cannot coexist with the others: a data array and prefix whose first two
dimensions differ or whose byte orders disagree, or a binary header whose length is not
a whole number of records. The static helpers ``_format_isint``, ``_intfmt``,
``_realfmt``, and ``_check_array_vs_prefix`` hold the shared logic, and
``_FORMAT_FROM_DTYPE`` in :mod:`vicar._DEFINITIONS` lists the dtypes that VICAR can
represent.

Two consequences matter when changing this code:

* **The label follows the arrays, never the reverse.** Arrays are stored as given,
  without conversion, and the label records their dtype and byte order. Reading a file
  produces native-order arrays, but an array a caller assigns keeps its byte order, and
  :meth:`~vicar.VicarImage.write_file` writes it in that order.
* **The structural parameters are not the user's to change.** ``_IMMUTABLE`` in
  :mod:`vicar._DEFINITIONS` lists them, and :class:`~vicar.VicarImage` refuses to assign
  or delete the first occurrence of any of them through item syntax. Later occurrences,
  such as those in an EOL label or a processing history, are ordinary metadata. The
  check lives in :class:`~vicar.VicarImage`, not :class:`~vicar.VicarLabel`, because a
  bare label has no arrays to stay consistent with, and the setters themselves update
  these parameters through the label directly.

Assigning None to :attr:`~vicar.VicarImage.array` removes the array without changing the
label, and :meth:`~vicar.VicarImage.write_file` refuses to write an image with no array.

Sharing
=======

:class:`~vicar.VicarImage` does not copy what it is given. Constructing an image from a
:class:`~vicar.VicarLabel` uses that label object, so changes made through either are
seen by both. :meth:`~vicar.VicarImage.copy` copies the label but shares the arrays;
:meth:`~vicar.VicarImage.deepcopy` copies everything. Preserve this distinction in a new
method, and say in its docstring which it does.

The Binary Header
=================

The binary header is opaque to the package: it is read and written as raw bytes.
:meth:`~vicar.VicarImage.binheader_array` interprets those bytes as a table of numbers
on request, taking the dtype from ``FMT_DEFAULT`` or the caller and the table shape from
``NR`` and ``NC`` when the label has them. This handles ISIS table files (IBIS format)
in which every column has the same format.

Label Access Through the Image
==============================

The methods in the ``Public methods inherited from the VicarLabel object`` section of
the source give an image the dictionary-like interface of its label. Apart from the
``_IMMUTABLE`` check in assignment and deletion, each delegates to the label unchanged.
A new public method of :class:`~vicar.VicarLabel` that callers should reach through an
image needs a delegating method here too, with its own docstring and its own entry in
the type stub.

See :class:`~vicar.VicarImage` in the :doc:`public reference </module>` and in the
:doc:`internal reference <dev_guide_internal_api>`, which includes the private methods
this chapter names.
