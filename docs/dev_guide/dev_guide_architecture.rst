============
Architecture
============

Class Diagram
=============

.. mermaid::

   classDiagram
       class VicarError {
       }
       class VicarLabel {
           -_names
           -_values
           -_formats
           -_strict
           -_filepath
           -_key_index
           -_unique_keys
           +filepath
           +__getitem__(key)
           +__setitem__(key, value)
           +__delitem__(key)
           +append(source)
           +insert(source, indx)
           +reorder(keys)
           +arg(key, value)
           +export(resize)
           +read_label(source)
           +write_label(filepath)
           -_update(names, vals, fmts)
           -_finish_update()
           -_interpret_source(source, required, fileio)
           -_args(key, mode)
       }
       class VicarImage {
           -_label
           -_array
           -_prefix
           -_binheader
           -_filepath
           +label
           +array
           +prefix
           +binheader
           +from_file(filepath, extraneous, strict)
           +from_array(array, strict)
           +write_file(filepath)
           +binheader_array(kind, size)
           -_read_file(filepath, extraneous, strict)
       }
       class _ValueFormat {
           <<namedtuple>>
           fmt
           name_blanks
           val_blanks
           sep_blanks
           listfmts
       }
       class _ListFormat {
           <<namedtuple>>
           fmt
           blanks_before
           blanks_after
       }
       class _LABEL_GRAMMAR {
           <<module>>
           parse_string(text)
       }
       class _DEFINITIONS {
           <<module>>
           _REQUIRED
           _IMMUTABLE
           _ENUMERATED_VALUES
           _DTYPE_FROM_FORMAT
           _FORMAT_FROM_DTYPE
       }
       ValueError <|-- VicarError
       VicarImage *-- "1" VicarLabel : label
       VicarLabel o-- "*" _ValueFormat : one per parameter
       _ValueFormat o-- "*" _ListFormat : one per list item
       VicarLabel ..> _LABEL_GRAMMAR : parses text with
       VicarLabel ..> _DEFINITIONS : validates against
       VicarImage ..> _DEFINITIONS : maps dtypes with

The package is small: two classes that do the work, one exception, and two private
modules of supporting definitions. The design rests on one division of labor.
:class:`~vicar.VicarLabel` knows everything about label text and nothing about binary
data. :class:`~vicar.VicarImage` knows how the binary data is laid out in a file, and
reaches into its label only to read and write the parameters that describe that layout.

The Label
=========

:class:`~vicar.VicarLabel` stores a label as three parallel lists, in label order:
``_names`` holds the parameter names, ``_values`` the values, and ``_formats`` the
formatting hints, one ``_ValueFormat`` or None per parameter. A name may occur more than
once, because the VICAR standard repeats parameters such as ``TASK``, ``USER``, and
``DAT_TIM`` once for each processing step, and the three lists are what preserve both
the duplicates and their order.

Two structures derived from the lists make lookups fast. ``_key_index`` maps each name,
and each ``(name, occurrence)`` pair, to the list positions where it appears, and
``_unique_keys`` gives every parameter a key that identifies it alone: its name if the
name occurs once, or ``(name, occurrence)`` otherwise. They are rebuilt lazily, as
:doc:`dev_guide_label` explains.

Label text enters through the grammar in :mod:`vicar._LABEL_GRAMMAR`, which turns it
into a list of tuples, and leaves through :meth:`~vicar.VicarLabel.export`, which renders
the lists back into text of the right length for the file. The formatting hints make the
round trip faithful: a label that is read and written without changes comes back with
the same spacing and number formats.

The tables in :mod:`vicar._DEFINITIONS` describe the standard: the required parameters
and their defaults, the parameters with a fixed set of legal values, the parameters that
must be non-negative integers, and the mappings between VICAR ``FORMAT`` codes and NumPy
dtypes.

The Image
=========

:class:`~vicar.VicarImage` owns exactly one :class:`~vicar.VicarLabel`, available as
:attr:`~vicar.VicarImage.label`, and up to three pieces of binary content:

* the data array, stored as a three-dimensional NumPy array in native byte order;
* the prefix, the bytes at the start of each data record that precede the image data,
  stored as a three-dimensional array whose last axis is the prefix width;
* the binary header, the records between the label and the data, stored as
  :class:`bytes` or as a NumPy array.

Each of these is set through a property setter that validates it against the other two
and then updates the structural parameters in the label: ``RECSIZE``, ``NLB``, ``NBB``,
``FORMAT``, the byte-order parameters, and the dimensions. This is the class's central
invariant: whenever an assignment succeeds, the label describes the arrays exactly, so
that :meth:`~vicar.VicarImage.write_file` can write the label and the arrays without
reconciling them. For the same reason, item assignment and deletion through the image
refuse to change the first occurrence of any parameter listed in ``_IMMUTABLE``.
:doc:`dev_guide_image` describes the setters in detail.

The rest of the :class:`~vicar.VicarImage` interface, such as item access, iteration,
and :meth:`~vicar.VicarImage.keys`, delegates to the label, so an image can be used
wherever its label could.

Reading a File
==============

Constructing a :class:`~vicar.VicarImage` from a path, or calling
:meth:`~vicar.VicarImage.from_file`, runs the private static method ``_read_file``:

1. Open the file through :class:`~filecache.file_cache_path.FCPath`, so that local paths
   and remote URLs behave the same.
2. Call :meth:`~vicar.VicarLabel.read_label`, which reads the first 40 bytes and matches
   ``LBLSIZE`` to learn the length of the top label, then reads that label. It parses
   the label loosely, with ``strict=False``, only to learn ``RECSIZE``, ``NLB``, and the
   dimensions, from which it locates the end of the data.
3. If another ``LBLSIZE`` begins at the end of the data, read the end-of-file (EOL)
   label there and append its text to the top label's. Any bytes after that are
   extraneous, and the ``extraneous`` option decides whether they are ignored, printed,
   raised as a warning or a :class:`~vicar.VicarError`, or returned.
4. Parse the combined label text, this time with the caller's ``strict`` setting.
5. Read the binary header and the data records, split each record into its prefix and
   data parts at ``NBB`` bytes, and convert the data to a native-order array of the
   dtype that ``FORMAT``, ``INTFMT``, and ``REALFMT`` describe, converting VAX
   floating-point values with ``rms-vax``.
6. Hand the label and the three arrays to the property setters, which validate them and
   bring the structural parameters up to date.

The constructor of :class:`~vicar.VicarLabel`, given a file, performs only the label part
of this, steps 2 through 4.

Writing a File
==============

:meth:`~vicar.VicarImage.write_file` relies on the setters' invariant. It calls
:meth:`~vicar.VicarLabel.export` with ``resize=True``, which enlarges ``LBLSIZE`` to a
whole number of records that holds the label, writes the label text, then the binary
header, then each record with its prefix bytes before its data bytes, and finally any
EOL label.

:meth:`~vicar.VicarLabel.write_label` is the other write path. It rewrites the label of
an existing file in place, without touching the data. It must keep the original
``LBLSIZE``, so it exports with ``resize=False``: whatever does not fit in the top label
moves to an EOL label after the data, and the file is truncated after it.
