=====================
Extending the Package
=====================

The package has no plugin mechanism; it is extended by editing its two classes and its
tables. These recipes cover the changes that come up most often. Each ends the same way:
add tests, update the docstrings and the README where they describe the behavior, and
run ``./scripts/run-all-checks.sh``.

Adding a Public Method
======================

1. Write the method in the section of ``src/vicar/vicarlabel.py`` or
   ``src/vicar/vicarimage.py`` where it belongs, under the banner comments that group the
   methods.
2. In a :class:`~vicar.VicarLabel` method, call ``_finish_update`` before reading
   ``_len``, ``_key_index``, or ``_unique_keys``, and make any change by building new
   lists and passing them to ``_update``. :doc:`dev_guide_label` explains both rules.
3. Write a complete docstring, with the types in annotation style, and add the method to
   the list of methods in the class docstring.
4. Declare the method in ``src/vicar/__init__.pyi`` with the same signature. stubtest
   fails until you do.
5. If callers should reach the method through an image too, add a method of the same
   name to :class:`~vicar.VicarImage` that delegates to its label, with its own
   docstring and its own stub entry.
6. Add tests to the ``tests/test_vicarlabel_*.py`` or ``tests/test_vicarimage_*.py`` file
   whose topic fits.

For example, a method that counts the occurrences of a name:

.. code-block:: python

   # src/vicar/vicarlabel.py, in class VicarLabel
   def count(self, name):
       """The number of occurrences of a parameter name in this label.

       Parameters:
           name (str): The parameter name.

       Returns:
           int: The number of occurrences; zero if the name is absent.
       """

       self._finish_update()
       return len(self._key_index.get(name, []))

.. code-block:: python

   # src/vicar/__init__.pyi, in class VicarLabel
   def count(self, name: str) -> int: ...

.. code-block:: python

   # tests/test_vicarlabel_access.py
   def test_vicarlabel_count() -> None:
       """count() returns the number of occurrences of a name."""

       label = VicarLabel([('A', 1), ('B', 2), ('A', 3)])
       assert label.count('A') == 2

Supporting Another Data Type
============================

Reading and writing data arrays rest on two tables in :mod:`vicar._DEFINITIONS`:
``_DTYPE_FROM_FORMAT`` maps a VICAR ``FORMAT`` code to a NumPy dtype for reading, and
``_FORMAT_FROM_DTYPE`` maps a dtype, as its kind and item size, to a ``FORMAT`` code and
whether it is an integer type, for writing. To support another format:

1. Add the ``FORMAT`` code to ``_DTYPE_FROM_FORMAT`` and to
   ``_ENUMERATED_VALUES['FORMAT']``, which validates the parameter.
2. Add the dtype to ``_FORMAT_FROM_DTYPE`` if the package should also write it. Two
   codes can read as the same dtype, as ``COMP`` and ``COMPLEX`` do, but each dtype
   writes as one code.
3. Check ``_read_file`` in ``src/vicar/vicarimage.py``, which chooses the byte order
   from ``INTFMT`` for integer kinds and from ``REALFMT`` for the others, and converts
   VAX floating-point data.
4. Add cases to ``tests/test_vicarimage_formats.py``, and a round trip through
   :meth:`~vicar.VicarImage.write_file` and :meth:`~vicar.VicarImage.from_file` in
   ``tests/test_vicarimage_write.py``.

.. code-block:: python

   # src/vicar/_DEFINITIONS.py; "NEWF" and "x8" stand for the new code and dtype
   _DTYPE_FROM_FORMAT = {...,
                         'NEWF': 'x8'}

   _FORMAT_FROM_DTYPE = {...,
                         'x8': ('NEWF', False)}

   _ENUMERATED_VALUES = {
       'FORMAT'  : {'BYTE', 'HALF', 'FULL', 'REAL', 'DOUB', 'COMP',
                    'WORD', 'LONG', 'COMPLEX', 'NEWF'},
       ...
   }

Adding a Required or Structural Parameter
=========================================

The tables in :mod:`vicar._DEFINITIONS` decide which parameters a label must have and
which a user may change:

* Add a parameter every label must carry to ``_REQUIRED``, at its position in the
  standard, with its default value. ``_REQUIRED_NAMES`` follows automatically.
* If its value is one of a fixed set, add the set to ``_ENUMERATED_VALUES``. If it must
  be a non-negative integer, add it to ``_REQUIRED_INTS``.
* If :class:`~vicar.VicarImage` derives it from the arrays, add it to ``_IMMUTABLE`` and
  set it in the property setter that owns it.

A new required parameter changes every label the package creates and every file it
writes, so the tests that compare complete labels or counts of parameters change too.

Adding a Key Form
=================

All key resolution happens in ``_args``, with the helpers ``_has_plus``, ``_add_plus``,
``_remove_plus``, and ``_get_name``. A new form of key needs a branch in each, for both
``'get'`` and ``'set'`` mode, and nothing else in the code. It does need documentation
in many places: every public method that takes a key describes the key forms in its
docstring, and so does the ``Notes About Dictionary Keys`` section of the
:class:`~vicar.VicarLabel` and :class:`~vicar.VicarImage` class docstrings. Add tests to
``tests/test_vicarlabel_keys.py``.

Changing How Values Are Written
===============================

The label text the package writes must parse back to the same values and formatting
hints. A change to :meth:`~vicar.VicarLabel.value_str` or
:meth:`~vicar.VicarLabel.name_value_str` therefore needs the matching change in the
parse actions of :mod:`vicar._LABEL_GRAMMAR`, and the reverse. Test the change in both
directions: in ``tests/test_label_grammar.py`` for parsing, and with a round trip from
text to a :class:`~vicar.VicarLabel` and back in ``tests/test_vicarlabel_export.py``.
