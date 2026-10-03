=========
The Label
=========

This chapter covers :class:`~vicar.VicarLabel`, in ``src/vicar/vicarlabel.py``, and the
grammar and definitions it relies on, in :mod:`vicar._LABEL_GRAMMAR` and
:mod:`vicar._DEFINITIONS`. :doc:`dev_guide_architecture` introduces the storage model;
this chapter covers what a developer needs in order to change it.

Storage and the Deferred Index
==============================

The content of a label is the three parallel lists ``_names``, ``_values``, and
``_formats``. Every operation that changes the content builds new lists and passes them
to ``_update``, which stores them and sets the flag ``_waiting_to_update``. None of them
modifies the lists in place, so a list obtained before a change still describes the
label as it was.

``_update`` deliberately does not rebuild the lookup structures. ``_finish_update`` does
that, and only when the flag is set: it recomputes ``_len``, builds ``_key_index`` and
``_unique_keys`` from the names, and clears the flag. A sequence of changes, such as the
many assignments :meth:`~vicar.VicarLabel.export` makes while preparing a label, then
costs one rebuild rather than one per change.

That deferral imposes the class's most important rule: **any method that reads**
``_len``, ``_key_index``, **or** ``_unique_keys`` **must call** ``_finish_update``
**first.** The public methods all do, directly or through a method that does. A new
method that skips the call works in most tests and fails whenever it runs straight after
a change.

``_key_index`` maps three kinds of key to a list of positions:

* each name to the positions of all its occurrences, in order;
* each ``(name, n)``, for every occurrence ``n`` counted from zero, to that occurrence's
  position;
* each ``(name, n - count)``, the same occurrence counted from the end, so that
  ``('TASK', -1)`` finds the last ``TASK``.

``_unique_keys`` holds, for each position, the key that iteration and
:meth:`~vicar.VicarLabel.keys` report: the bare name when it occurs once, or
``(name, n)`` when it repeats.

Resolving Keys
==============

Every form of key the public API accepts is resolved by one private method, ``_args``,
which returns a position or a list of positions together with a flag saying whether the
parameter exists. It runs in one of two modes:

* ``'get'`` mode, for reading and deleting, raises :class:`KeyError`,
  :class:`IndexError`, or :class:`ValueError` when the key matches nothing.
* ``'set'`` mode, for assignment, returns the position at which a new parameter should
  be inserted when the key matches nothing, with the flag False. A key of
  ``(name, after)`` places the new parameter at the end of the section that ``after``
  begins, which is how assignment adds a parameter to the right processing step.

A trailing ``+`` on the name changes the meaning of a key: in ``'get'`` mode it selects
every matching occurrence rather than the first, and in ``'set'`` mode it forces an
insertion even when the name already exists. The static helpers ``_has_plus``,
``_add_plus``, and ``_remove_plus`` read and edit that suffix in any form of key, and
``_get_name`` extracts the name. A new key form belongs in ``_args`` and in these
helpers, nowhere else; :meth:`~vicar.VicarLabel.arg`, item access, assignment, deletion,
and :meth:`~vicar.VicarLabel.reorder` all go through them.

Assignment to an existing parameter that supplies no hints of its own keeps the
parameter's previous hints where they still apply. An integer format, such as ``%d``,
survives the assignment of an integer, and a floating-point format, such as ``%f``,
``%e``, or ``%g``, survives the assignment of a float; otherwise the format is dropped
and only the spacing is kept.

Turning Sources into Lists
==========================

The constructor, :meth:`~vicar.VicarLabel.append`, :meth:`~vicar.VicarLabel.insert`, and
assignment all accept the same kinds of source: a file, a path, label text, a dict, a
list of tuples, or a single tuple. ``_interpret_source``
converts any of them into the three lists:

1. A file or a path is read with :meth:`~vicar.VicarLabel.read_label`. A string is
   treated as a path only if a file of that name exists; otherwise it is label text.
2. Label text is parsed by ``_LABEL_GRAMMAR``. A dict becomes a list of tuples.
3. Each tuple's name is checked by ``_validate_name``, its value and hints are split by
   ``_interpret_value_format``, and the value is checked by ``_validate_value``.
4. If ``required`` is True, as it is only for the constructor, ``_validate_required``
   adds any missing required parameter with its default value and checks the values of
   those present.

Strict mode, the default, applies the VICAR standard to names and values: a name has at
most 32 characters and is upper case, a string is printable 7-bit ASCII, and a list is
non-empty with items of one type. With ``strict=False`` these checks are skipped, because
real files often break them; :class:`~vicar.VicarImage` reads files that way when asked.
The checks that remain in either mode are the ones the code cannot work without: a name
the grammar accepts, values of a supported type, and the rules for required parameters.

Required Parameters
===================

``_REQUIRED`` in :mod:`vicar._DEFINITIONS` lists the parameters every label must have,
in the order the standard gives them, with their defaults. The defaults for the
byte-order parameters and ``HOST`` come from the platform the code runs on. Three
further tables constrain the required parameters:

* ``_ENUMERATED_VALUES`` gives the legal values of ``FORMAT``, ``ORG``, the byte-order
  parameters, ``DIM``, ``EOL``, and ``N4``.
* ``_REQUIRED_INTS`` lists the parameters that must be non-negative integers.
* ``_REQUIRED_NAMES`` is the set of required names, used to refuse the deletion of the
  first occurrence of any of them.

``LBLSIZE`` must always be the first parameter. ``_validate_required`` moves it to the
front when it builds a label and raises :class:`~vicar.VicarError` when a later change
would move it, and :meth:`~vicar.VicarLabel.reorder` restores it to the front after
rearranging the rest.

The Grammar
===========

:mod:`vicar._LABEL_GRAMMAR` defines ``_LABEL_GRAMMAR``, a ``pyparsing`` grammar for a
complete label. Its parse actions turn each ``NAME=VALUE`` statement into a tuple of the
name, the value, and the formatting information needed to write it back the same way:
the number format when it differs from what :class:`str` would produce, and the counts
of blanks around the equal sign and after the value when they are not the standard ones.
List values carry the same information for each item. The module docstring lists every
tuple shape the grammar can produce, and ``tests/test_label_grammar.py`` covers each.

``_interpret_value_format`` and its helpers ``_interpret_valfmt`` and
``_interpret_listfmt`` turn that trailing information, or the hints a caller supplies in
the same form, into a ``_ValueFormat`` for the parameter and a ``_ListFormat`` for each
list item. A parameter with no hints stores None. :meth:`~vicar.VicarLabel.value_str` and
:meth:`~vicar.VicarLabel.name_value_str` render a parameter from its value and hints;
with none, the result is the standard ``NAME=VALUE`` followed by two blanks.

The grammar and the hint tuples are two descriptions of one format. A change to how a
value is written needs a matching change in the grammar's parse actions, so that the
text the package writes parses back to the same value and hints.

Exporting
=========

:meth:`~vicar.VicarLabel.export` produces the text written to a file, as two strings:
the top label, padded with null characters to ``LBLSIZE`` bytes, and the EOL label, which
is empty when everything fits. It first calls ``_prep_for_export``, which modifies the
label itself:

* It derives ``N1``, ``N2``, and ``N3`` from ``NS``, ``NL``, ``NB``, and ``ORG``.
* It removes every ``LBLSIZE`` after the first.
* With ``resize=True``, or when ``LBLSIZE`` is zero or not a multiple of ``RECSIZE``, it
  sets ``LBLSIZE`` to the smallest whole number of records that holds the label and sets
  ``EOL`` to 0.
* With ``resize=False``, it keeps ``LBLSIZE``. If the label does not fit, it sets ``EOL``
  to 1 and inserts a second ``LBLSIZE``, sized in whole records for the parameters that
  do not fit, where the top label ends; :meth:`~vicar.VicarLabel.export` then splits the
  text at that second ``LBLSIZE``.

Because ``_prep_for_export`` changes the label, calling
:meth:`~vicar.VicarLabel.export` is not free of side effects. Code that must leave a
label unchanged should export a :meth:`~vicar.VicarLabel.copy`.

See :class:`~vicar.VicarLabel` in the :doc:`public reference </module>` and in the
:doc:`internal reference <dev_guide_internal_api>`, which includes the private methods
this chapter names.
