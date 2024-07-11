##########################################################################################
# vicar/vicarlabel.py
##########################################################################################
"""Class to support accessing, reading, and modifying VICAR labels."""

import io
import numbers
import os
import pathlib
import pyparsing
import re

from collections import namedtuple
from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR, _NAME
from vicar._DEFINITIONS import (_ENUMERATED_VALUES, _LBLSIZE_WIDTH, _REQUIRED,
                                _REQUIRED_INTS, _REQUIRED_NAMES)

_LBLSIZE_PATTERN = re.compile(r'LBLSIZE *= *(\d+)')

_ValueFormat = namedtuple('_ValueFormat', ['fmt', 'name_blanks', 'val_blanks',
                                           'sep_blanks', 'listfmts'])
_ListFormat = namedtuple('_ListFormat', ['fmt', 'blanks_before', 'blanks_after'])


class VicarError(ValueError):
    """ValueError subclass for violations of the VICAR format standard."""
    pass


class VicarLabel():
    """Class to support accessing, reading, modifying, and writing VICAR labels.

    **Properties:**

        * `filepath`: The file path associated with this VicarLabel.

    **Core Methods:**

        * `append`: Append one or more parameters to the end of this label.
        * `arg`: The index of a parameter name within this label.
        * `args`: Iterator over the numeric indices of the parameters in this label.
        * `as_string`: A string representing all or part of this label.
        * `copy`: An independent (deep) copy of this VicarLabel.
        * `export`: Returns a label parameter string of the form `NAME=VALUE`.
        * `from_file`: Construct a VicarLabel object from the content of a VICAR data
          file.
        * `get`: Retrieve a label parameter value or return a default.
        * `insert`: Insert one or more parameters into this label.
        * `items`: Iterator over the `(name, value)` tuples in this label.
        * `keys`: Iterator over the parameter names in this label as unique keys.
        * `name_value_str`: Returns a label parameter string of the form `NAME=VALUE`.
        * `names`: Iterator over the parameter names in this label.
        * `read_label`: Read the label string(s) from a file.
        * `reorder`: Reorder the parameters in this label.
        * `value_str`: Formats a label parameter value.
        * `values`: Iterator over the parameter values in this label.
        * `write_label`: Write this label into a data file, replacing an existing label.

    **Python Syntax Support Methods:**

        * `__contains__`: Enables "`name in label`" syntax.
        * `__delitem__`: Enables "`del label[name]`" syntax.
        * `__eq__`: Enables "`a == b`", the test of whether two labels are equal.
        * `__getitem__`: Enables "`label[name]`" dictionary-like syntax.
        * `__iter__`: Enables "`for key in label:`" syntax.
        * `__len__`: Enables "`len(label)`", the number of parameters in the given
          VicarLabel.
        * `__repr__`: Enables "`repr(label)`", similar to the "`str(label)`", but with the
          class name included.
        * `__setitem__`: Enables "`label[name] = value`" dictionary-like syntax.
        * `__str__`: Enables "`str(label)`", returning a string representing the content
          of a label.

    **Notes About Dictionary Keys:**

        When using dictionary-like syntax to reference a parameter in a VICAR label, a
        rich set of options are available. For example, if `label` is a VicarLabel object,
        then:

            * `label[n]` where `n` is an integer refers to the "nth" parameter in the
              label. `n` can be positive or negative.
            * `label[name]` where `name` is a string refers to the first occurrence in the
              label of a parameter with this name.
            * `label[name,n]` refers to the "nth" occurrence in the label of a parameter
              with this name. `n` can be positive or negative.
            * `label[name, after]` where both items are strings refers to the first
              occurrence of parameter `name` after the first occurrence of parameter
              `after` and before the second occurrence of `after`.
            * `label[name, after, value]` refers to the first occurrence of parameter
              `name` after the first location where `after` equals `value` and before the
              next occurrence of `after`.

        The last two options make it easy to reference a VICAR label parameter that is
        repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies
        the occurrence of `DAT_TIM` applicable to `TASK='COPY'` when there might be other
        `TASK` sections of the label containing other values of `DAT_TIM`.

        Append a "+" to `name` to expand upon the function's behavior. With "get"
        operations, a list is returned identifying all of the occurrences of the selected
        name rather than just the first or "nth". With "set" operations, a new occurrence
        of `name` is inserted into the label even if the a parameter of the given name is
        already present.

    **Notes About VICAR Label Formatting Hints:**

        Formatting hints can be included wherever a VICAR parameter value is specified.
        When defining label parameters using a list of tuples, use (name, value, hints...)
        instead of (name, value). Elsewhere, simply replace the value by a tuple (value,
        hints...).

        Hints can be specified using up to four items:

            ([`format`][[[, `name_blanks`], `val_blanks`], `sep_blanks`])

        where:

            * `format` is a format string, e.g., "%+7d" or "%7.3f".
            * `name_blanks` is the number of blank characters after the name and before
              the equal sign; zero by default.
            * `val_blanks` is the number of blank characters after the equal sign and
              before the value; zero by default.
            * `sep_blanks` is the number of blanks after the value and before the next
              label parameter or the label's end; two by default.

        Note the use of square brackets in the tuple expression above. If the first hint
        value is a string, it is interpreted as `format`; otherwise, the `format` is
        unspecified. After the optional format, values are interpreted as numbers of
        blanks. If only one int is provided, it defines `sep_blanks`, with `val_blanks`
        and `name_blanks` set to zero. If two trailing ints are provided, they define
        `val_blanks` and `sep_blanks`, with `name_blanks` set to zero.

        For example, if the name is "TEXP" and the value is 1.5, this is how hint values
        are interpreted::

                <no hints>        = ("", 0, 0, 0)     -> "TEXP=1.5  "
                "%.3f"            = ("%.3f", 0, 0, 0) -> "TEXP=1.500  "
                ("%.3f", 4)       = ("%.3f", 0, 0, 4) -> "TEXP=1.500    "
                ("%.3f", 1, 4)    = ("%.3f", 0, 1, 4) -> "TEXP= 1.500    "
                ("%.3f", 2, 1, 4) = ("%.3f", 2, 1, 4) -> "TEXP  = 1.500    "
                4                 = ("", 0, 0, 4)     -> "TEXP=1.5    "
                (1, 4)            = ("", 0, 1, 4)     -> "TEXP= 1.5    "
                (2, 1, 4)         = ("", 2, 1, 4)     -> "TEXP  = 1.5    "

        When the parameter value is a list, it is also possible to embed formatting
        information on an item by item basis. Replace any item value by a tuple:

            (`item` [, `format`][[, `blanks_before`], `blanks_after`])

        where:

            * `format` is a format string, e.g., "%+07d", "%12.3e" or "%.4f".
            * `blanks_before` is the number of blanks before the value, after the left
              parenthesis or comma; zero is the default.
            * `blanks_after` is the number of blanks after the value and before the next
              next comma or the right parenthesis; zero is the default.

        Here are some examples of a list with embedded formatting for a parameter named
        "XY" with a value [7,6]::

            [(7, "%+02d"), 6]       = [(7, "%+02d", 0, 0), 6] -> "XY=[+07, 6]  "
            [(7, 2), 6]             = [(7, "", 0, 2), 6]      -> "XY=[7  , 6]  "
            [(7, 1, 2), 6])         = [(7, "", 1, 2), 6]      -> "XY=[ 7  , 6]  "
            [(7, "%02d", 2), 6])    = [(7, "%02d", 0, 2), 6]  -> "XY=[07  , 6]  "
            [(7, "%02d", 1, 2), 6]) = [(7, "%02d", 1, 2), 6]  -> "XY=[ 07  , 6]  "
    """

    def __init__(self, source=None, strict=True):
        """Constructor for a VicarLabel.

        Parameters:
            source (file, pathlib.Path, str, None, dict, or list):
                A representation of a VICAR label:

                * *file*: The label string is read from the given, open file.
                * *pathlib.Path*: The label string is read from the referenced file.
                * *str*: First, a check is performed to see if it is path to an existing
                  file. If so, the label is read from that file; otherwise, the string is
                  itself interpreted as a VICAR label string.
                * *None*: The returned VicarLabel only contains the required parameters
                  with their default values.
                * *dict*: The label parameters are the names of the dictionary keys, given
                  in the order they were entered into the dictionary. Each dictionary
                  value is either the VICAR parameter value or a tuple(value, formatting
                  hints).
                * *list*: The label is derived from the given sequence of (name, value) or
                  (name, value, formatting hints) tuples.

                See ``Notes`` for details about formatting hints.

            strict (bool, optional):
                True (the default) to require strict conformance to the VICAR standard;
                False for a looser version of the standard. The standard is described
                here:

                    https://pds-rings.seti.org/help/VICAR_file_fmt.pdf

                When `strict` is False:

                    * names can exceed 32 characters and contain lower case letters.
                    * string values need not be pure 7-bit ASCII.
                    * lists can contain a mixture of types.
                    * lists can be empty.

        Raises:
            OSError: If the source is given as a file path that cannot be read.
            TypeError: If the source is an unrecognized type or contains an unrecognized
                type.
            VicarError: If the source violates the VICAR standard or a required VICAR
                parameter has an invalid value.

        Notes:
            Formatting hints can be included wherever a VICAR parameter value is
            specified. When defining label parameters using a list of tuples, use (name,
            value, hints...) instead of (name, value). Elsewhere, simply replace the value
            by a tuple (value, hints...).

            Hints can be specified using up to four items:

                ([`format`][[[, `name_blanks`], `val_blanks`], `sep_blanks`])

            where:

                * `format` is a format string, e.g., "%+7d" or "%7.3f".
                * `name_blanks` is the number of blank characters after the name and
                  before the equal sign; zero by default.
                * `val_blanks` is the number of blank characters after the equal sign and
                  before the value; zero by default.
                * `sep_blanks` is the number of blanks after the value and before the next
                  label parameter or the label's end; two by default.

            Note the use of square brackets in the tuple expression above. If the first
            hint value is a string, it is interpreted as `format`; otherwise, the `format`
            is unspecified. After the optional format, values are interpreted as numbers
            of blanks. If only one int is provided, it defines `sep_blanks`, with
            `val_blanks` and `name_blanks` set to zero. If two trailing ints are provided,
            they define `val_blanks` and `sep_blanks`, with `name_blanks` set to zero.

            For example, if the name is "TEXP" and the value is 1.5, this is how hint
            values are interpreted::

                <no hints>        = ("", 0, 0, 0)     -> "TEXP=1.5  "
                "%.3f"            = ("%.3f", 0, 0, 0) -> "TEXP=1.500  "
                ("%.3f", 4)       = ("%.3f", 0, 0, 4) -> "TEXP=1.500    "
                ("%.3f", 1, 4)    = ("%.3f", 0, 1, 4) -> "TEXP= 1.500    "
                ("%.3f", 2, 1, 4) = ("%.3f", 2, 1, 4) -> "TEXP  = 1.500    "
                4                 = ("", 0, 0, 4)     -> "TEXP=1.5    "
                (1, 4)            = ("", 0, 1, 4)     -> "TEXP= 1.5    "
                (2, 1, 4)         = ("", 2, 1, 4)     -> "TEXP  = 1.5    "

            When the parameter value is a list, it is also possible to embed formatting
            information on an item by item basis. Replace any item value by a tuple:

                (`item` [, `format`][[, `blanks_before`], `blanks_after`])

            where:

                * `format` is a format string, e.g., "%+07d", "%12.3e" or "%.4f".
                * `blanks_before` is the number of blanks before the value, after the left
                  parenthesis or comma; zero is the default.
                * `blanks_after` is the number of blanks after the value and before the
                  next comma or the right parenthesis; zero is the default.

            Here are some examples of a list with embedded formatting for a parameter
            named "XY" with a value [7,6]::

                [(7, "%+02d"), 6]       = [(7, "%+02d", 0, 0), 6] -> "XY=[+07, 6]  "
                [(7, 2), 6]             = [(7, "", 0, 2), 6]      -> "XY=[7  , 6]  "
                [(7, 1, 2), 6])         = [(7, "", 1, 2), 6]      -> "XY=[ 7  , 6]  "
                [(7, "%02d", 2), 6])    = [(7, "%02d", 0, 2), 6]  -> "XY=[07  , 6]  "
                [(7, "%02d", 1, 2), 6]) = [(7, "%02d", 1, 2), 6]  -> "XY=[ 07  , 6]  "
        """

        self._strict = bool(strict)

        names, vals, fmts, self._filepath = self._interpret_source(source, required=True,
                                                                   fileio=True)
        self._update(names, vals, fmts)

    def _update(self, names, vals, fmts):
        """Internal method to define or re-define the label's content.

        Parameters:
            names (list[str]): List of names, already validated.
            vals (list): List of values, already validated.
            fmts (list[_ValueFormat or None]): List of formatting hints, validated.
        """

        self._names = names
        self._values = vals
        self._formats = fmts
        self._waiting_to_update = True      # defer indexing during updates

    def _finish_update(self):
        """Internal method to finish defining or re-defining the label's content.

        This must be called before any operation on the object.
        """

        if not self._waiting_to_update:
            return

        self._len = len(self._names)

        # Dictionary keyed by name, returning list of indices
        self._key_index = {}
        for i, name in enumerate(self._names):
            self._key_index[name] = self._key_index.get(name, []) + [i]

        # Create ordered list of name or (name, occurrence) if name is not unique
        self._unique_keys = list(self._names)

        # Augment list with (name, occurrence) for duplicates
        for i, name in enumerate(self._names):
            indices = self._key_index[name]
            occs = len(indices)
            k = indices.index(i)
            if occs != 1:
                self._unique_keys[i] = (name, k)
            self._key_index[(name, k)] = [i]
            self._key_index[(name, k - occs)] = [i]

        self._waiting_to_update = False

    ######################################################################################
    # Properties
    ######################################################################################

    @property
    def filepath(self):
        """The file path associated with this VicarLabel.

        Returns:
            pathlib.Path or None:
                The Path if this object is associated with a file; None otherwise.
        """

        return self._filepath

    @filepath.setter
    def filepath(self, value):
        """Set the file path associated with this VicarLabel.

        Parameters:
            value (pathlib.Path or None):
                The Path to the file associated with this object; None if this object is
                not associated with a file.
        """

        if value:
            self._filepath = pathlib.Path(value)
        else:
            self._filepath = None

    ######################################################################################
    # Support for the Standard Python API
    ######################################################################################

    def copy(self):
        """An independent (deep) copy of this VicarLabel.

        Returns:
            VicarLabel: The copy.
        """

        label = VicarLabel(source=[], strict=self._strict)
        label._filepath = self._filepath
        vals = [list(v) if isinstance(v, list) else v for v in self._values]  # new lists
        label._update(list(self._names), vals, list(self._formats))
        return label

    def __len__(self):
        """The number of keywords in the VICAR label.

        Returns:
            int: Number of keywords.
        """

        self._finish_update()
        return self._len

    def __eq__(self, other):
        """VicarLabels are equal if they have the same parameter names in the same order.
        Formatting and filepath are ignored.

        VicarLabels are equal if their parameters and values are all the same; formatting
        hints need not be the same.

        Parameters:
            other (VicarLabel): Second VicarLabel to compare with this.

        Returns:
            bool: True if the names and values are equal.
        """

        if not isinstance(other, VicarLabel):
            return False

        return self._names == other._names and self._values == other._values

    def __str__(self):
        return self.as_string()

    def __repr__(self):
        return 'VicarLabel("""' + self.as_string(sep='\n\n') + '""")'

    ######################################################################################
    # Validation Utililties
    ######################################################################################

    def _interpret_source(self, source, required=False, fileio=False):
        """Interpret and validate a source object.

        Parameters:
            source (file, pathlib.Path, str, None, dict, list, or tuple):
                A representation of VICAR label content:

                * *file*: The label string is read from the given, open file.
                * *pathlib.Path*: The label string is read from the referenced file.
                * *str*: First, a check is performed to see if it is path to an existing
                  file. If so, the label is read from that file; otherwise, the string is
                  itself interpreted as a VICAR label string.
                * *None*: The returned VicarLabel only contains the required parameters
                  with their default values.
                * *dict*: The label parameters are the names of the dictionary keys, given
                  in the order they were entered into the dictionary. Each dictionary
                  value is either the VICAR parameter value or a tuple(value, formatting
                  hints).
                * *list*: The label is derived from the given sequence of (name, value) or
                  (name, value, formatting hints) tuples.
                * *tuple*: A single parameter defined by (name, value) or (name, value,
                  formatting hints).

                See ``Notes`` for details about formatting hints.

            required (bool, optional):
                True to insert any required VICAR parameters that are missing.

            fileio (bool, optional):
                True to allow the source to be read from a file, file path string, or
                pathlib.Path object. In this case, the file path is returned in addition
                to the lists.

        Returns:
            (list, list, list[, pathlib.Path or None]): A tuple containing:

            * list[str]: List of names.
            * list[int, float, str, or list]: List of values.
            * list[_ValueFormat or None]: List of formatting hints.
            * pathlib.Path or None, optional: The pathlib.Path of the file if the label
              was read from a file; otherwise, None. Included only if `fileio` is True.

        Raises:
            OSError: If `fileio` is True but a file could not be read.
            TypeError: If the source is an unrecognized type or contains an unrecognized
                type, or if a format string is incompatible with a parameter value.
            VicarError: If the source violates the VICAR standard or a required VICAR
                parameter has an invalid value.

        Notes:
            Formatting hints can be included wherever a VICAR parameter value is
            specified. When defining label parameters using a list of tuples, use (name,
            value, hints...) instead of (name, value). Elsewhere, simply replace the value
            by a tuple (value, hints...).

            Hints can be specified using up to four items:

                ([`format`][[[, `name_blanks`], `val_blanks`], `sep_blanks`])

            where:

                * `format` is a format string, e.g., "%+7d" or "%7.3f".
                * `name_blanks` is the number of blank characters after the name and
                  before the equal sign; zero by default.
                * `val_blanks` is the number of blank characters after the equal sign and
                  before the value; zero by default.
                * `sep_blanks` is the number of blanks after the value and before the next
                  label parameter or the label's end; two by default.

            Note the use of square brackets in the tuple expression above. If the first
            hint value is a string, it is interpreted as `format`; otherwise, the `format`
            is unspecified. After the optional format, values are interpreted as numbers
            of blanks. If only one int is provided, it defines `sep_blanks`, with
            `val_blanks` and `name_blanks` set to zero. If two trailing ints are provided,
            they define `val_blanks` and `sep_blanks`, with `name_blanks` set to zero.

            For example, if the name is "TEXP" and the value is 1.5, this is how hint
            values are interpreted::

                <no hints>        = ("", 0, 0, 0)     -> "TEXP=1.5  "
                "%.3f"            = ("%.3f", 0, 0, 0) -> "TEXP=1.500  "
                ("%.3f", 4)       = ("%.3f", 0, 0, 4) -> "TEXP=1.500    "
                ("%.3f", 1, 4)    = ("%.3f", 0, 1, 4) -> "TEXP= 1.500    "
                ("%.3f", 2, 1, 4) = ("%.3f", 2, 1, 4) -> "TEXP  = 1.500    "
                4                 = ("", 0, 0, 4)     -> "TEXP=1.5    "
                (1, 4)            = ("", 0, 1, 4)     -> "TEXP= 1.5    "
                (2, 1, 4)         = ("", 2, 1, 4)     -> "TEXP  = 1.5    "

            When the parameter value is a list, it is also possible to embed formatting
            information on an item by item basis. Replace any item value by a tuple:

                (`item` [, `format`][[, `blanks_before`], `blanks_after`])

            where:

                * `format` is a format string, e.g., "%+07d", "%12.3e" or "%.4f".
                * `blanks_before` is the number of blanks before the value, after the left
                  parenthesis or comma; zero is the default.
                * `blanks_after` is the number of blanks after the value and before the
                  next comma or the right parenthesis; zero is the default.

            Here are some examples of a list with embedded formatting for a parameter
            named "XY" with a value [7,6]::

                [(7, "%+02d"), 6]       = [(7, "%+02d", 0, 0), 6] -> "XY=[+07, 6]  "
                [(7, 2), 6]             = [(7, "", 0, 2), 6]      -> "XY=[7  , 6]  "
                [(7, 1, 2), 6])         = [(7, "", 1, 2), 6]      -> "XY=[ 7  , 6]  "
                [(7, "%02d", 2), 6])    = [(7, "%02d", 0, 2), 6]  -> "XY=[07  , 6]  "
                [(7, "%02d", 1, 2), 6]) = [(7, "%02d", 1, 2), 6]  -> "XY=[ 07  , 6]  "
        """

        # Handle files
        if fileio:
            filepath = None
            if isinstance(source, io.IOBase):
                filepath = pathlib.Path(source.name)
                source = VicarLabel.read_label(source)
            elif isinstance(source, pathlib.Path):
                filepath = source
                source = VicarLabel.read_label(source)
            elif isinstance(source, str) and os.path.exists(source):
                filepath = pathlib.Path(source)
                source = VicarLabel.read_label(filepath)

        # Convert to list of tuples
        if isinstance(source, tuple):
            source = [source]   # a single tuple becomes a list of tuples
        elif source is None:
            source = []
        elif isinstance(source, dict):
            source = [(k,) + (v if isinstance(v, tuple) else (v,))
                      for k,v in source.items()]
        elif isinstance(source, str):
            try:
                source = _LABEL_GRAMMAR.parse_string(source).as_list()
            except pyparsing.ParseException as e:
                raise VicarError('VICAR parsing failure: ' + str(e))
        elif not isinstance(source, list):
            raise TypeError('Not a recognized source type: ' + type(source).__name__)

        # Validate list element types
        for item in source:
            if not isinstance(item, tuple) or len(item) < 2:
                raise TypeError('Not a valid (name, value) tuple: ' + repr(item))

        # Extract names, values, formats and validate
        names = []
        vals = []
        fmts = []
        for item in source:
            VicarLabel._validate_name(item[0], strict=self._strict)
            (val, fmt) = VicarLabel._interpret_value_format(item[1:])
            VicarLabel._validate_value(val, item[0], strict=self._strict)
            names.append(item[0])
            vals.append(val)
            fmts.append(fmt)

        # Insert required parameters if necessary
        if required:
            names, vals, fmts = VicarLabel._validate_required(names, vals, fmts,
                                                              append=True)

        if fileio:
            return (names, vals, fmts, filepath)

        return (names, vals, fmts)

    @staticmethod
    def _validate_name(name, strict=True):
        """Raise a VicarError if this is not valid name for a VICAR label parameter.

        Parameters:
            name (str): VICAR parameter name.
            strict (bool, optional): True for strict VICAR conformance, False for loose.

        Raises:
            VicarError: If this is not a valid VICAR parameter name.
        """

        if not isinstance(name, str):
            raise VicarError('VICAR name is not a string: ' + repr(name))

        try:
            _ = _NAME.parse_string(name)
        except pyparsing.ParseException:
            raise VicarError('Invalid VICAR name string: ' + repr(name))

        if strict:
            if len(name) > 32:
                raise VicarError('VICAR name exceeds 32 characters: ' + repr(name))
            if not name.isupper():
                raise VicarError('VICAR name is not upper case: ' + repr(name))

    @staticmethod
    def _validate_value(value, name, strict=True):
        """Raise a VicarError if this is not valid value for a VICAR label parameter.

        Parameters:
            value (int, float, string, or list): VICAR parameter value.
            name (str): Name of the VICAR parameter.
            strict (bool, optional): True for strict VICAR conformance, False for loose.

        Raises:
            VicarError: If this is not a valid VICAR parameter value.
        """

        if isinstance(value, numbers.Real):
            return

        if isinstance(value, str):
            if strict and not all(32 <= ord(c) <= 126 for c in value):
                raise VicarError(f'{name} string value is not ASCII: ' + repr(value))
            return

        if isinstance(value, list):
            if len(value) == 0:
                if strict:
                    raise VicarError(f'{name} list value is empty: ' + repr(value))
                return

            if strict:
                # Make sure all the list elements have the same type
                if isinstance(value[0], numbers.Integral):
                    type_ = numbers.Integral
                elif isinstance(value[0], numbers.Real):
                    type_ = numbers.Real
                elif isinstance(value[0], str):
                    type_ = str
                else:
                    type_name = type(value[0]).__name__
                    raise VicarError(f'{name} list item has invalid type {type_name}: '
                                     + repr(value))

                if all(isinstance(v, type_) for v in value[1:]):
                    return

                type_name = type(value[0]).__name__
                raise VicarError(f'{name} list items are not all of type {type_name}')

            for v in value:
                if not isinstance(v, (numbers.Real, str)):
                    type_name = type(v).__name__
                    raise VicarError(f'{name} list item has invalid type {type_name}: '
                                     + repr(v))

            return

        type_ = type(value)
        raise VicarError(f'{name} value type {type_.__name__} is invalid: ' + repr(value))

    @staticmethod
    def _interpret_value_format(item):
        """Get the value and optional format from a (value, optional format info) tuple.

        Parameters:
            item (tuple): VICAR parameter value followed by optional formatting hints.

        Returns:
            (any, _ValueFormat or None): A tuple containing:

            * int, float, string, or list: The interpreted value.
            * _ValueFormat or None: Formatting hints if provided; None otherwise.

        Raises:
            TypeError: If the format string is incompatible with the value.
            VicarError: If this is not a valid tuple of formatting hints or is
                incompatible with the value type.
        """

        def validate_tuplefmt(value, tuplefmt):
            if not tuplefmt or not tuplefmt.fmt:
                return

            fmt = tuplefmt.fmt
            _ = fmt % value     # TypeError on failure
            if isinstance(value, numbers.Integral):
                if fmt[-1] not in 'di':
                    raise TypeError('invalid format for int: ' + repr(fmt))
            elif isinstance(value, numbers.Real):
                if fmt[-1] not in 'eEfFgG':
                    raise TypeError('invalid format for float: ' + repr(fmt))
            elif isinstance(value, str):    # pragma: no branch
                raise TypeError('formats for strings are disallowed: ' + repr(fmt))

        # If this parameter value is a list, interpret its values and formatting
        if isinstance(item[0], list):
            value = []
            listfmts = []
            for subval in item[0]:

                # Tuple case: (value[, format][[, blanks_before], blanks_after])
                if isinstance(subval, tuple):
                    listfmt = VicarLabel._interpret_listfmt(subval[1:])
                    validate_tuplefmt(subval[0], listfmt)
                    value.append(subval[0])
                    listfmts.append(listfmt)
                else:
                    value.append(subval)
                    listfmts.append(None)

            if not any(listfmts):
                listfmts = []

        # Otherwise, the value is easy and there are no list formats
        else:
            value = item[0]
            listfmts = []

        # Interpret the rest of the tuple
        valfmt = VicarLabel._interpret_valfmt(item[1:], listfmts)
        validate_tuplefmt(value, valfmt)
        return (value, valfmt)

    def _interpret_valfmt(hints, listfmts=[]):
        """Get the _ValueFormat from a value or tuple.

        Parameters:
            hints (tuple): Value format hints.
            listfmt (list[_ListFormat[, optional): Formats for list elements.

        Returns:
            _ValueFormat or None:
                Interpreted _ValueFormat; None if no formatting hints were provided.

        Raises:
            VicarError: If this is not a valid tuple of formatting hints.
        """

        if not hints:
            if listfmts:
                return _ValueFormat('', 0, 0, 0, listfmts)
            return None

        if isinstance(hints[0], str):
            fmt = hints[0]
            ints = hints[1:]
        else:
            fmt = ''
            ints = hints

        while len(ints) < 3:
            ints = (0,) + ints

        if (len(ints) > 3
                or not all(isinstance(i, numbers.Integral) and i >= 0 for i in ints)):
            raise VicarError('invalid value formatting hints: ' + repr(hints))

        return _ValueFormat(fmt, *ints, listfmts)

    def _interpret_listfmt(hints):
        """Get the _ListFormat from a value or tuple.

        Parameters:
            hints (tuple): List element format hints.

        Returns:
            _ListFormat or None: Interpreted _ListFormat; None if there is no format.
        """

        if isinstance(hints[0], str):
            fmt = hints[0]
            ints = hints[1:]
        else:
            fmt = ''
            ints = hints

        while len(ints) < 2:
            ints = (0,) + ints

        if (len(ints) > 2
                or not all(isinstance(i, numbers.Integral) and i >= 0 for i in ints)):
            raise VicarError('invalid value formatting hints: ' + repr(hints))

        return _ListFormat(fmt, *ints)

    @staticmethod
    def _validate_required(names, vals, fmts, append=False):
        """Validate that the required VICAR parameters are all present and valid.

        Parameters:
            names (list[str]): List of names.
            vals (list[int, float, str, or list]): List of values.
            fmts (list[_ValueFormat or None]): List of formatting hints.
            append (bool, optional): True to append any missing required VICAR parameters.

        Returns:
            (list, list, list): A tuple containing:

            * list[str]: List of names.
            * list[int, float, str, or list]: List of values.
            * list[_ValueFormat or None]: List of formatting hints.

        Raises:
            VicarError: A name or value violates the VICAR standard.
        """

        name_set = set(names)
        for item in _REQUIRED:
            name = item[0]
            if name in name_set:
                k = names.index(name)
                value = vals[k]
                if name in _ENUMERATED_VALUES:
                    if value not in _ENUMERATED_VALUES[name]:
                        raise VicarError(f'Invalid {name} value: {repr(value)}; '
                                         f'must be in {_ENUMERATED_VALUES[name]}')
                elif name in _REQUIRED_INTS:
                    if not isinstance(value, numbers.Integral) or value < 0:
                        raise VicarError(f'Invalid {name} value: {repr(value)}; '
                                         f'must be a non-negative integer')
            elif append:    # pragma: no branch
                names.append(name)
                vals.append(item[1])
                fmts.append(None)

            else:           # pragma: no cover; can't get here currently
                raise VicarError(f'missing required VICAR parameter "{name}"')

        # Move LBLSIZE to the front if necessary
        if names[0] != 'LBLSIZE':
            if append:
                k = names.index('LBLSIZE')
                name = names.pop(k)
                val = vals.pop(k)
                fmt = fmts.pop(k)

                names = [name] + names
                vals = [val] + vals
                fmts = [fmt] + fmts
            else:
                raise VicarError('VICAR parameter "LBLSIZE" must be first')

        return (names, vals, fmts)     # same list objects as input

    ######################################################################################
    # Object Modification Operations
    ######################################################################################

    def append(self, source):
        """Append the additional content to the end of this label.

        Parameters:
            source (file, pathlib.Path, str, None, dict, list, or tuple):
                A representation of VICAR label content:

                * *file*: The label string is read from the given, open file.
                * *pathlib.Path*: The label string is read from the referenced file.
                * *str*: First, a check is performed to see if it is path to an existing
                  file. If so, the label is read from that file; otherwise, the string is
                  itself interpreted as a VICAR label string.
                * *None*: The returned VicarLabel only contains the required parameters
                  with their default values.
                * *dict*: The label parameters are the names of the dictionary keys, given
                  in the order they were entered into the dictionary. Each dictionary
                  value is either the VICAR parameter value or a tuple(value, formatting
                  hints).
                * *list*: The label is derived from the given sequence of (name, value) or
                  (name, value, formatting hints) tuples.
                * *tuple*: A single parameter defined by (name, value) or (name, value,
                  formatting hints).

                See ``Notes`` for details about formatting hints.

        Raises:
            OSError: If the source is given as a file path that cannot be read.
            TypeError: If the source is an unrecognized type or contains an unrecognized
                type.
            VicarError: If the source violates the VICAR standard or a required VICAR
                parameter has an invalid value.

        Notes:
            Formatting hints can be included wherever a VICAR parameter value is
            specified. When defining label parameters using a list of tuples, use (name,
            value, hints...) instead of (name, value). Elsewhere, simply replace the value
            by a tuple (value, hints...).

            Hints can be specified using up to four items:

                ([`format`][[[, `name_blanks`], `val_blanks`], `sep_blanks`])

            where:

                * `format` is a format string, e.g., "%+7d" or "%7.3f".
                * `name_blanks` is the number of blank characters after the name and
                  before the equal sign; zero by default.
                * `val_blanks` is the number of blank characters after the equal sign and
                  before the value; zero by default.
                * `sep_blanks` is the number of blanks after the value and before the next
                  label parameter or the label's end; two by default.

            Note the use of square brackets in the tuple expression above. If the first
            hint value is a string, it is interpreted as `format`; otherwise, the `format`
            is unspecified. After the optional format, values are interpreted as numbers
            of blanks. If only one int is provided, it defines `sep_blanks`, with
            `val_blanks` and `name_blanks` set to zero. If two trailing ints are provided,
            they define `val_blanks` and `sep_blanks`, with `name_blanks` set to zero.

            For example, if the name is "TEXP" and the value is 1.5, this is how hint
            values are interpreted::

                <no hints>        = ("", 0, 0, 0)     -> "TEXP=1.5  "
                "%.3f"            = ("%.3f", 0, 0, 0) -> "TEXP=1.500  "
                ("%.3f", 4)       = ("%.3f", 0, 0, 4) -> "TEXP=1.500    "
                ("%.3f", 1, 4)    = ("%.3f", 0, 1, 4) -> "TEXP= 1.500    "
                ("%.3f", 2, 1, 4) = ("%.3f", 2, 1, 4) -> "TEXP  = 1.500    "
                4                 = ("", 0, 0, 4)     -> "TEXP=1.5    "
                (1, 4)            = ("", 0, 1, 4)     -> "TEXP= 1.5    "
                (2, 1, 4)         = ("", 2, 1, 4)     -> "TEXP  = 1.5    "

            When the parameter value is a list, it is also possible to embed formatting
            information on an item by item basis. Replace any item value by a tuple:

                (`item` [, `format`][[, `blanks_before`], `blanks_after`])

            where:

                * `format` is a format string, e.g., "%+07d", "%12.3e" or "%.4f".
                * `blanks_before` is the number of blanks before the value, after the left
                  parenthesis or comma; zero is the default.
                * `blanks_after` is the number of blanks after the value and before the
                  next comma or the right parenthesis; zero is the default.

            Here are some examples of a list with embedded formatting for a parameter
            named "XY" with a value [7,6]::

                [(7, "%+02d"), 6]       = [(7, "%+02d", 0, 0), 6] -> "XY=[+07, 6]  "
                [(7, 2), 6]             = [(7, "", 0, 2), 6]      -> "XY=[7  , 6]  "
                [(7, 1, 2), 6])         = [(7, "", 1, 2), 6]      -> "XY=[ 7  , 6]  "
                [(7, "%02d", 2), 6])    = [(7, "%02d", 0, 2), 6]  -> "XY=[07  , 6]  "
                [(7, "%02d", 1, 2), 6]) = [(7, "%02d", 1, 2), 6]  -> "XY=[ 07  , 6]  "
        """

        names, vals, fmts, _ = self._interpret_source(source, required=False, fileio=True)

        names = self._names + names
        vals = self._values + vals
        fmts = self._formats + fmts

        self._update(names, vals, fmts)

    def insert(self, source, indx):
        """Insert the given content into this label at the specified index.

        Parameters:
            source (file, pathlib.Path, str, dict, list, or tuple):
                A representation of VICAR label content:

                * *file*: The label string is read from the given, open file.
                * *pathlib.Path*: The label string is read from the referenced file.
                * *str*: First, a check is performed to see if it is path to an existing
                  file. If so, the label is read from that file; otherwise, the string is
                  itself interpreted as a VICAR label string.
                * *dict*: The label parameters are the names of the dictionary keys, given
                  in the order they were entered into the dictionary. Each dictionary
                  value is either the VICAR parameter value or a tuple(value, formatting
                  hints).
                * *list*: The label is derived from the given sequence of (name, value) or
                  (name, value, formatting hints) tuples.
                * *tuple*: A single parameter defined by (name, value) or (name, value,
                  formatting hints).

                See ``Notes`` for details about formatting hints.

            indx (int): The integer index defining the location at which to insert the new
                content. If the index is non-negative, the new new content will begin at
                this index. If negative, the new content will end just before this index.
                To append, to the label, use indx = len(self).

        Raises:
            OSError: If the source is given as a file path that cannot be read.
            TypeError: If the source is an unrecognized type or contains an unrecognized
                type.
            VicarError: If the source violates the VICAR standard or a required VICAR
                parameter has an invalid value.

        Notes:
            Formatting hints can be included wherever a VICAR parameter value is
            specified. When defining label parameters using a list of tuples, use (name,
            value, hints...) instead of (name, value). Elsewhere, simply replace the value
            by a tuple (value, hints...).

            Hints can be specified using up to four items:

                ([`format`][[[, `name_blanks`], `val_blanks`], `sep_blanks`])

            where:

                * `format` is a format string, e.g., "%+7d" or "%7.3f".
                * `name_blanks` is the number of blank characters after the name and
                  before the equal sign; zero by default.
                * `val_blanks` is the number of blank characters after the equal sign and
                  before the value; zero by default.
                * `sep_blanks` is the number of blanks after the value and before the next
                  label parameter or the label's end; two by default.

            Note the use of square brackets in the tuple expression above. If the first
            hint value is a string, it is interpreted as `format`; otherwise, the `format`
            is unspecified. After the optional format, values are interpreted as numbers
            of blanks. If only one int is provided, it defines `sep_blanks`, with
            `val_blanks` and `name_blanks` set to zero. If two trailing ints are provided,
            they define `val_blanks` and `sep_blanks`, with `name_blanks` set to zero.

            For example, if the name is "TEXP" and the value is 1.5, this is how hint
            values are interpreted::

                <no hints>        = ("", 0, 0, 0)     -> "TEXP=1.5  "
                "%.3f"            = ("%.3f", 0, 0, 0) -> "TEXP=1.500  "
                ("%.3f", 4)       = ("%.3f", 0, 0, 4) -> "TEXP=1.500    "
                ("%.3f", 1, 4)    = ("%.3f", 0, 1, 4) -> "TEXP= 1.500    "
                ("%.3f", 2, 1, 4) = ("%.3f", 2, 1, 4) -> "TEXP  = 1.500    "
                4                 = ("", 0, 0, 4)     -> "TEXP=1.5    "
                (1, 4)            = ("", 0, 1, 4)     -> "TEXP= 1.5    "
                (2, 1, 4)         = ("", 2, 1, 4)     -> "TEXP  = 1.5    "

            When the parameter value is a list, it is also possible to embed formatting
            information on an item by item basis. Replace any item value by a tuple:

                (`item` [, `format`][[, `blanks_before`], `blanks_after`])

            where:

                * `format` is a format string, e.g., "%+07d", "%12.3e" or "%.4f".
                * `blanks_before` is the number of blanks before the value, after the left
                  parenthesis or comma; zero is the default.
                * `blanks_after` is the number of blanks after the value and before the
                  next comma or the right parenthesis; zero is the default.

            Here are some examples of a list with embedded formatting for a parameter
            named "XY" with a value [7,6]::

                [(7, "%+02d"), 6]       = [(7, "%+02d", 0, 0), 6] -> "XY=[+07, 6]  "
                [(7, 2), 6]             = [(7, "", 0, 2), 6]      -> "XY=[7  , 6]  "
                [(7, 1, 2), 6])         = [(7, "", 1, 2), 6]      -> "XY=[ 7  , 6]  "
                [(7, "%02d", 2), 6])    = [(7, "%02d", 0, 2), 6]  -> "XY=[07  , 6]  "
                [(7, "%02d", 1, 2), 6]) = [(7, "%02d", 1, 2), 6]  -> "XY=[ 07  , 6]  "
        """

        names, vals, fmts, _ = self._interpret_source(source, required=False, fileio=True)

        names = self._names[:indx] + names + self._names[indx:]
        vals = self._values[:indx] + vals + self._values[indx:]
        fmts = self._formats[:indx] + fmts + self._formats[indx:]

        # Make sure the required parameters are still valid
        names, vals, fmts = VicarLabel._validate_required(names, vals, fmts, append=False)

        self._update(names, vals, fmts)

    def reorder(self, *keys):
        """Re-order one or more specified parameters inside this object.

        Parameters:
            *keys (list[int, name, or tuple]):
                Two or more indexing keys, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`. Also if an index is duplicated in the
                new order.

        Notes:
            The first key is left in place, and subsequent keys are positioned after it in
            the order given. Use "" in front of the first key if you want the listed keys
            to be first.
        """

        move_to_front = (keys[0] == '')
        if move_to_front:
            keys = keys[1:]

        order = [self.arg(k) for k in keys]
        order_set = set(order)
        if len(order) != len(order_set):
            raise ValueError('duplicated index in reorder')

        before = []
        if not move_to_front:
            for i in range(order[0]):
                if i not in order_set:
                    before.append(i)

        order = before + order
        order_set = set(order)
        for i in range(self._len):
            if i not in order_set:
                order.append(i)

        names = [self._names[i] for i in order]
        values = [self._values[i] for i in order]
        formats = [self._formats[i] for i in order]

        # LBLSIZE restored to first
        if names[0] != 'LBLSIZE':
            k = names.index('LBLSIZE')
            order = [k] + [i for i in range(len(names)) if i != k]
            names = [names[i] for i in order]
            values = [values[i] for i in order]
            formats = [formats[i] for i in order]

        self._update(names, values, formats)

    ######################################################################################
    # Indexing Support
    ######################################################################################

    def _args(self, key, mode='get'):
        """The numerical index or indices of the keyed item in the VICAR label.

        Parameters:
            key (int, name, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

                Append a "+" to `name` to expand upon the function's behavior. With "get",
                it returns a list of matching indices rather than a single index. With
                "set", it will identify the index where a new parameter is to be inserted
                if the key is not found.

            mode (str, optional): One of:

                * "get": an error will be raised if the key does not exist.
                * "set": a single index will be returned, indicating where in the label
                  to insert the new parameter.

        Returns:
            (int or list, bool): A tuple containing:

            * int or list[int]: The index or list of indices that identify matching
              parameters. If the key contains a name ending in "+", this is a list
              starting with the "nth" occurrence; otherwise, it is a single int.
            * bool:  True if the identified parameter already exists; False if `mode` is
              "set" and the int is the location to insert a new parameter.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of  a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        self._finish_update()

        assert mode in {'get', 'set'}, 'invalid mode: ' + repr(mode)

        # Handle an integer key
        if isinstance(key, numbers.Integral):
            if key < 0:
                key += self._len
            if key >= 0 and key < self._len:
                return key, True
            raise IndexError('list index out of range: ' + repr(key))

        # Check the key format and extract the name
        has_plus = VicarLabel._has_plus(key)
        key = VicarLabel._remove_plus(key)

        # Handle name alone
        if isinstance(key, str):
            if mode == 'set' and has_plus:
                return self._len, False

            indices = self._key_index.get(key, [])
            if indices:
                if has_plus:
                    return indices, True
                else:
                    return indices[0], True
            elif mode == 'set':
                return self._len, False

            raise KeyError(key)

        # Handle (name, occurrence)
        if len(key) == 2 and isinstance(key[1], numbers.Integral):
            name, indx = key
            indices = self._key_index.get(name, [])

            # Handle a reference one beyond the last valid index
            if mode == 'set' and indx == len(indices):
                return self._len, False

            if not indices:
                raise KeyError(name)    # different message from indx out of range

            # Return if the index is in range
            if -len(indices) <= indx < len(indices):
                if mode == 'get' and has_plus:
                    return indices[indx:], True
                else:
                    return indices[indx], True

            raise IndexError('list index out of range: ' + repr(key))

        # Handle (name, after_name) or (name, after_name, after_value)
        if len(key) in (2,3) and isinstance(key[1], str):
            name, after_name = key[:2]
            indices = self._key_index.get(after_name, [])
            if not indices:
                raise KeyError(after_name)

            # Get the start and stop indices within this "after_name" section
            if len(key) == 3:
                matches = [i for i in indices if self._values[i] == key[2]]
                if not matches:
                    raise ValueError(f'{after_name} never has value {repr(key[2])}')
                start = matches[0]
            else:
                start = indices[0]

            k = indices.index(start)
            if k == len(indices) - 1:
                stop = self._len
            else:
                stop = indices[k+1]

            if mode == 'set' and has_plus:
                return stop, False

            # Find the indices with matching names
            indices = [i for i in range(start,stop) if self._names[i] == name]
            if indices:
                if mode == 'get' and has_plus:
                    return indices, True
                return indices[0], True
            elif mode == 'set':
                return stop, False

            raise KeyError(key)

        raise TypeError('invalid key type: ' + repr(key))

    @staticmethod
    def _add_plus(key):
        """Insert a plus, if absent, at the end of the name within the indexing key."""

        if isinstance(key, str):
            return key.rstrip('+') + '+'

        if isinstance(key, tuple) and key and isinstance(key[0], str):
            return (key[0].rstrip('+') + '+',) + key[1:]

        return key

    @staticmethod
    def _remove_plus(key):
        """Remove a plus, if present, from the end of the name within the indexing key."""

        if isinstance(key, str):
            return key.rstrip('+')

        if isinstance(key, tuple) and key and isinstance(key[0], str):
            return (key[0].rstrip('+'),) + key[1:]

        return key

    @staticmethod
    def _has_plus(key):
        """True if there is a plus at the end of the name within the indexing key."""

        if isinstance(key, str):
            return key.endswith('+')

        if isinstance(key, tuple) and key and isinstance(key[0], str):
            return key[0].endswith('+')

        return False

    def _get_name(self, key):
        """Get a name, if present, from the indexing key and remove any plus."""

        if isinstance(key, numbers.Integral):
            return self.names()[key]

        if isinstance(key, str):
            return key.rstrip('+')

        if isinstance(key, tuple) and key and isinstance(key[0], str): # pragma: no branch
            return key[0].rstrip('+')

        return ''   # pragma: no cover; shouldn't happen

    ######################################################################################
    # Indexing Operations
    ######################################################################################

    def arg(self, key, value=None):
        """The numerical index or indices of the keyed item in the VICAR label.

        Parameters:
            key (int, name, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

                Append a "+" to the name to return a list of all indices where the
                constraints are satisfied, starting with the first or "nth".

            value (int, float, or string, optional):
                If provided, the identified parameter must equal this value. For an
                integer key, if the indexed parameter does not have this value, ValueError
                is raised. For any key involving a name, values of the named parameter
                that do not match `value` are skipped over until the one(s) with the
                correct value are found.

        Returns:
            int or list[int]:
                The index or list of indices that identify matching parameters. If the key
                contains a name ending in "+", this is a list starting with the "nth"
                occurrence; otherwise, it is a single int.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        if value is not None:

            # We need to get all matches, regardless of "+"
            has_plus = VicarLabel._has_plus(key)
            key = VicarLabel._add_plus(key)

            indices, _ = self._args(key, mode='get')
            if isinstance(indices, numbers.Integral):
                indices = [indices]
            indices = [i for i in indices if self._values[i] == value]
            if not indices:
                raise ValueError(f'index {key} never has value {repr(value)}')

            return indices if has_plus else indices[0]

        index_or_indices, _ = self._args(key, mode='get')
        return index_or_indices

    def __getitem__(self, key):
        """Retrieve the value or values of the VICAR parameter defined by key, using
        various indexing options.

        Parameters:
            key (int, name, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

                Append a "+" to the name to return a list of all values where the
                constraints are satisfied, starting with the first or "nth".

        Returns:
            int, float, string, or list:
                If `key` contains a name ending in "+", this is the list of values of the
                matching parameters, starting with the "nth". Otherwise, it is the single
                matching value.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        indices, _ = self._args(key, mode='get')
        if isinstance(indices, list):
            return [self._values[i] for i in indices]

        return self._values[indices]

    def get(self, key, default):
        """Retrieve the value of the VICAR parameter defined by the given key, using
        various indexing options.

        If the key is not found, return a specified default value.

        Parameters:
            key (int, str, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

                Append a "+" to the name to return a list of all values where the
                constraints are satisfied, starting with the first or "nth".

            default (int, float, str, or list): The value to return if the key is not
                found.

        Returns:
            int, float, str, or list:
                If a name is provided that ends in a plus, the returned value will be the
                list of all values of the selected key, or else `[default]` if the key
                would raise an error.

                Otherwise, the returned value is that of the key if present, or `default`
                if it is not.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        try:
            return self.__getitem__(key)
        except (IndexError, KeyError, TypeError, ValueError, VicarError):
            if VicarLabel._has_plus(key):
                return [default]

            return default

    def __setitem__(self, key, value):
        """Set the value of the VICAR parameter defined by the given key; define a new
        parameter name and value if necessary.

        Parameters:
            key (int, str, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

                Append a "+" to the name to force a new occurrence of the key to be
                inserted, even if the key already exists.

            value (int, float, string, list, or tuple):
                Value to assign to the indexed entry in the label.

                Optional formatting can be included if a user wants additional control
                over how this value will be formatted in the label string will be
                formatted, by replacing the value with a tuple (value, hints...). See
                ``Notes`` for details about formatting hints.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.

        Notes:
            Formatting hints can be included wherever a VICAR parameter value is
            specified; simply replace the value by a tuple (value, hints...).

            Hints can be specified using up to four items:

                ([`format`][[[, `name_blanks`], `val_blanks`], `sep_blanks`])

            where:

                * `format` is a format string, e.g., "%+7d" or "%7.3f".
                * `name_blanks` is the number of blank characters after the name and
                  before the equal sign; zero by default.
                * `val_blanks` is the number of blank characters after the equal sign and
                  before the value; zero by default.
                * `sep_blanks` is the number of blanks after the value and before the next
                  label parameter or the label's end; two by default.

            Note the use of square brackets in the tuple expression above. If the first
            hint value is a string, it is interpreted as `format`; otherwise, the `format`
            is unspecified. After the optional format, values are interpreted as numbers
            of blanks. If only one int is provided, it defines `sep_blanks`, with
            `val_blanks` and `name_blanks` set to zero. If two trailing ints are provided,
            they define `val_blanks` and `sep_blanks`, with `name_blanks` set to zero.

            For example, if the name is "TEXP" and the value is 1.5, this is how hint
            values are interpreted::

                <no hints>        = ("", 0, 0, 0)     -> "TEXP=1.5  "
                "%.3f"            = ("%.3f", 0, 0, 0) -> "TEXP=1.500  "
                ("%.3f", 4)       = ("%.3f", 0, 0, 4) -> "TEXP=1.500    "
                ("%.3f", 1, 4)    = ("%.3f", 0, 1, 4) -> "TEXP= 1.500    "
                ("%.3f", 2, 1, 4) = ("%.3f", 2, 1, 4) -> "TEXP  = 1.500    "
                4                 = ("", 0, 0, 4)     -> "TEXP=1.5    "
                (1, 4)            = ("", 0, 1, 4)     -> "TEXP= 1.5    "
                (2, 1, 4)         = ("", 2, 1, 4)     -> "TEXP  = 1.5    "

            When the parameter value is a list, it is also possible to embed formatting
            information on an item by item basis. Replace any item value by a tuple:

                (`item` [, `format`][[, `blanks_before`], `blanks_after`])

            where:

                * `format` is a format string, e.g., "%+07d", "%12.3e" or "%.4f".
                * `blanks_before` is the number of blanks before the value, after the left
                  parenthesis or comma; zero is the default.
                * `blanks_after` is the number of blanks after the value and before the
                  next comma or the right parenthesis; zero is the default.

            Here are some examples of a list with embedded formatting for a parameter
            named "XY" with a value [7,6]::

                [(7, "%+02d"), 6]       = [(7, "%+02d", 0, 0), 6] -> "XY=[+07, 6]  "
                [(7, 2), 6]             = [(7, "", 0, 2), 6]      -> "XY=[7  , 6]  "
                [(7, 1, 2), 6])         = [(7, "", 1, 2), 6]      -> "XY=[ 7  , 6]  "
                [(7, "%02d", 2), 6])    = [(7, "%02d", 0, 2), 6]  -> "XY=[07  , 6]  "
                [(7, "%02d", 1, 2), 6]) = [(7, "%02d", 1, 2), 6]  -> "XY=[ 07  , 6]  "
        """

        # Handle an integer key
        if isinstance(key, numbers.Integral):

            self._finish_update()

            # Create a very short list of tuples and validate
            name = self._names[key]         # IndexError if out of range
            source = [(name,) + (value if isinstance(value, tuple) else (value,))]

            names, vals, fmts = self._interpret_source(source, required=False,
                                                       fileio=False)

            # Default to the pre-existing format if it works
            valfmt = fmts[0]
            if valfmt is None:
                valfmt = self._formats[key]
                if valfmt:
                    if valfmt.fmt:
                        if isinstance(value, numbers.Integral):
                            if valfmt.fmt[-1] not in 'di':
                                valfmt = _ValueFormat('', *valfmt[1:])
                        else:
                            if valfmt.fmt[-1] not in 'eEfFgG':
                                valfmt = _ValueFormat('', *valfmt[1:])
                    else:   # preserve spacing only
                        valfmt = _ValueFormat('', *valfmt[1:-1], [])

            # Create new lists
            key += (self._len if key < 0 else 0)
            names = self._names[:key] + names + self._names[key+1:]
            vals = self._values[:key] + vals + self._values[key+1:]
            fmts = self._formats[:key] + [valfmt] + self._formats[key+1:]

            # Make sure the required parameters are still valid, then update
            names, vals, fmts = VicarLabel._validate_required(names, vals, fmts,
                                                              append=False)
            self._update(self._names, vals, fmts)
            return

        # See if this is a new or existing parameter and get its new location
        indx, exists = self._args(key, mode='set')

        # For an update to an existing parameter, make a recursive call
        if exists:
            self.__setitem__(indx, value)

        # Otherwise, do the insert
        else:
            name = self._get_name(key)
            source = [(name,) + (value if isinstance(value, tuple) else (value,))]
            self.insert(source, indx)

    def __delitem__(self, key):
        """Delete the value of the VICAR parameter identified by the given key.

        Parameters:
            key (int, str, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

                Append a "+" to `name` to delete all of the label parameters whose names
                match the constraints, starting with the first or "nth".

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section
                of the label defined by `after_name` and `after_value`), or if the key
                format is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        indices, _ = self._args(key, mode='get')
        if not isinstance(indices, list):
            indices = [indices]

        # Make sure every deletion is legal
        for indx in indices:
            name = self._names[indx]
            if name in _REQUIRED_NAMES and self._key_index[name][0] == indx:
                raise VicarError(f'{name} is a required parameter')

        # Make copies of lists
        names = list(self._names)
        vals = list(self._values)
        fmts = list(self._formats)

        # Delete starting from end so indices don't change
        for indx in indices[::-1]:
            names.pop(indx)
            vals.pop(indx)
            fmts.pop(indx)

        self._update(names, vals, fmts)

    def __contains__(self, key):
        """True if the given key can be used to index the VICAR label.

        Parameters:
            key (int, str, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

        Returns:
            bool: True if the key is found within this label.
        """

        try:
            indx, _ = self._args(key, mode='get')
        except (IndexError, KeyError, TypeError, ValueError, VicarError):
            return False

        return True

    ######################################################################################
    # String Methods
    ######################################################################################

    def value_str(self, key):
        """The value of the given parameter as it will appear in the label.

        Parameters:
            key (int, str, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

        Returns:
            str: The VICAR-compliant string representing the value of the selected
                parameter.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        def _scalar_str(value, fmt=''):

            if fmt:
                return fmt % value

            if isinstance(value, numbers.Integral):
                return str(value)
            if isinstance(value, numbers.Real):
                return _float_str(value)

            return "'" + value.replace("'", "''") + "'"

        def _float_str(value):

            result = repr(value)
            mantissa, e, expo = result.partition('e')
            head, dot, tail = mantissa.partition('.')
            (_, sign, head) = head.rpartition('-')

            e = e.upper()
            dot = '.'

            if tail in ('0',''):
                return sign + head + dot + e + expo

            splitter = re.compile(r'(.*?)(00000|99999)(.*)')
            match = splitter.match(tail)
            if not match:
                return result

            (before, repeats, _) = match.groups()
            if repeats[0] == '0':
                return sign + head + dot + before + e + expo

            if not before:          # "1.99999" -> "2."
                head = str(int(head) + 1)
                value = float(sign + head + dot + e + expo)
                return _float_str(value)

            # Increment tail but preserve leading zeros: "1.0299999" -> "1.03"
            fmt = '%0' + str(len(before)) + 'd'
            tail = fmt % (int(before) + 1)
            return sign + head + dot + tail + e + expo

        ################
        # Active code...
        ################

        self._finish_update()

        key = VicarLabel._remove_plus(key)
        arg = self.arg(key)
        name = self._names[arg]
        value = self._values[arg]
        valfmt = self._formats[arg] or _ValueFormat('', 0, 0, 0, [])

        result = [valfmt.val_blanks * ' ']
        sep_blanks = valfmt.sep_blanks

        # Handle LBLSIZE, which always occupies 16 blanks, left-justified
        if name == 'LBLSIZE':
            valstr = str(value)
            result.append(valstr)
            sep_blanks = _LBLSIZE_WIDTH - 2 - len(valstr)

        # Handle a list
        elif isinstance(value, list):
            result.append('(')
            listfmts = valfmt.listfmts or len(value) * [_ListFormat('', 0, 0)]
            for v, f in zip(value, listfmts):
                if f:
                    result += [f.blanks_before * ' ', _scalar_str(v, f.fmt),
                               f.blanks_after * ' ']
                else:
                    result.append(_scalar_str(v))
                result.append(',')

            result[-1] = ')'

        # Handle a scalar
        else:
            result.append(_scalar_str(value, valfmt.fmt))

        # Append right padding
        result.append(sep_blanks * ' ')

        return ''.join(result)

    def name_value_str(self, key, pad=True):
        """Convert one entry in the dictionary to a string of the form "NAME=VALUE".

        Parameters:
            key (int, str, or tuple): The indexing key, interpreted as follows:

                * *int* = `n`: The "nth" parameter in the label. `n` can be positive or
                  negative.
                * *str* = `name`: The first occurrence in the label of a parameter with
                  this name.
                * (*str*, *int*) = (`name`, `n`): The "nth" occurrence in the label of a
                  parameter with this name. `n` can be positive or negative.
                * (*str*, *str*) = (`name`, `after`): The first occurrence of parameter
                  `name` after the first occurrence of parameter `after` and before the
                  second occurrence of `after`.
                * (*str*, *str*, *any*) = (`name`, `after`, `value`): The first occurrence
                  of parameter `name` after the first location where `after` equals
                  `value` and before the next occurrence of `after`.

                The last two options make it easy to reference a VICAR label parameter
                that is repeated. For example, "`label['DAT_TIM', 'TASK', 'COPY']`"
                uniquely identifies the occurrence of `DAT_TIM` applicable to
                `TASK='COPY'` when there might be other `TASK` sections of the label
                containing other values of `DAT_TIM`.

            pad (bool, optional):
                If True, the returned string will end with at least one blank character.

        Returns:
            str: A "NAME=VALUE" string compliant with the VICAR standard.

        Raises:
            IndexError: If any numeric component of the key is out of range.
            KeyError: If the parameter name is not present in the label (or the section of
                the label defined by `after_name` and `after_value`), or if the key format
                is unrecognized.
            TypeError: If the key is not a recognized type or contains a component that is
                not of a recognized type.
            ValueError: If no identified parameter equals `value` or if no occurrence of
                `after_name` equals `after_value`.
        """

        key = VicarLabel._remove_plus(key)
        k = self.arg(key)
        name = self._names[k]
        valfmt = self._formats[k] or _ValueFormat('', 0, 0, 0, [])
        valstr = self.value_str(key)
        result = [name, valfmt.name_blanks * ' ', '=', valstr]

        if pad and not valstr.endswith(' '):
            result.append('  ')

        return ''.join(result)

    def _prep_for_export(self, resize=True):
        """Update the label's LBLSIZE and EOL values in preparation for export.

        Parameters:
            resize (bool, optional):
                If True, LBLSIZE will be modified to accommodate the new content.
                Otherwise, the current value of LBLSIZE will be preserved and any overflow
                content will be placed into an end-of-file ("EOL") label. In this case, a
                second LBLSIZE parameter will mark the starting location of this label.
        """

        self._finish_update()

        lblsize = self['LBLSIZE']
        recsize = self['RECSIZE']
        if lblsize == 0 or lblsize % recsize != 0:
            resize = True

        self._n123_from_nbls()      # fix N1, N2, N3

        # Remove any extra LBLSIZE values
        while ('LBLSIZE',1) in self:
            del self[('LBLSIZE',1)]

        # Track the lengths of the "name=value" pairs
        eol = 0
        length = 0
        for k in range(self._len):
            name_value = self.name_value_str(k, pad=True)
            newlen = length + len(name_value)
            if not resize and newlen > lblsize:
                eol = 1
                label_count = k - 1     # number of parameters in the first VICAR label
                break

            length = newlen

        self['EOL'] = eol

        if eol:
            length = len(name_value)
            for k in range(label_count + 1, self._len):
                name_value = self.name_value_str(k, pad=True)
                length += len(name_value)

            eol_lblsize = len('LBLSIZE=') + _LBLSIZE_WIDTH + length
            eol_recs = (eol_lblsize + recsize - 1) // recsize
            eol_lblsize = eol_recs * recsize
            self['LBLSIZE+'] = eol_lblsize
            self.reorder(label_count, ('LBLSIZE',1))

        elif resize:
            nrecs = (length + recsize - 1) // recsize
            self['LBLSIZE'] = nrecs * recsize

    def export(self, resize=True):
        """Export this VicarLabel to text strings.

        Parameters:
            resize (bool, optional):
                If True, LBLSIZE will be modified to accommodate the new content.
                Otherwise, the current value of LBLSIZE will be preserved and any overflow
                content will be placed into an end-of-file label.

        Returns:
            (str, str): A tuple containing:

            * str: The VICAR label at the top of the file, as constrained by the internal
              values of LBLSIZE and RECSIZE. The string is padded with null characters to
              the full length specified by LBLSIZE.
            * str: The VICAR end-of-file label; empty if all the label content fits within
              the specified LBLSIZE.

        Note:
            The returned strings must be encoded as "latin8" bytes before writing them
            into a data file.
        """

        self._prep_for_export(resize=resize)

        pairs = []
        for k in range(self._len):
            if self._names[k] == 'LBLSIZE':
                k_eol = k
            pairs.append(self.name_value_str(k, pad=True))

        if k_eol:
            labels = [''.join(pairs[:k_eol]), ''.join(pairs[k_eol:])]
        else:
            labels = [''.join(pairs), '']

        for i in range(len(labels)):
            label = labels[i]
            lblsize = self.get(('LBLSIZE', i), 0)
            labels[i] = label + (lblsize - len(label)) * '\0'

        return labels

    def as_string(self, start=0, stop=None, sep=''):
        """The content of this label as a string.

        Parameters:
            start (int, optional):
                Index or key of the first parameter to include in the string.
            stop (int, optional):
                Index or key just after the last parameter to include in the string.
            sep (str, optional):
                Optional characters to insert before a second LBLSIZE. For example, use
                "\\n" to create a string with a line break before any extension label.

        Returns:
            str: A label string compliant with the VICAR standard.
        """

        start = self.arg(start)
        stop = self._len if stop is None else min(self._len, self.arg(stop))

        label = []
        for k in range(start, stop):
            name_value = self.name_value_str(k, pad=True)

            # Add optional separator before a second LBLSIZE
            if sep and k > 0 and self._names[k] == 'LBLSIZE':
                label.append(sep)

            label.append(name_value)

        return ''.join(label)

    ######################################################################################
    # Iterators
    ######################################################################################

    def __iter__(self):
        """Iterator over the unique names or (name, occurrence) pairs in the label.

        Returns:
            iterator:
                An iterator over the parameter keys within this label, in order. The key
                is the parameter name if it is unique or (name, occurrence number)
                otherwise.
        """

        self._finish_update()

        self._counter = 0
        return self

    def __next__(self):

        i = self._counter
        if i >= self._len:
            raise StopIteration

        self._counter += 1
        return self._unique_keys[i]

    def names(self, pattern=None):
        """Iterator over the names in this label.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            list: The list of the matching parameter names within this label, in order.
        """

        self._finish_update()

        if pattern:
            pattern = re.compile(pattern, re.I)
            return [n for n in self._names if pattern.fullmatch(n)]

        return list(self._names)        # return a copy

    def keys(self, pattern=None):
        """Iterator over the keys of the parameters within this label.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            list:
                The list of the parameter keys within this label, in order. The key is the
                parameter name if it is unique or (name, occurrence number) otherwise.
        """

        self._finish_update()

        if pattern:
            pattern = re.compile(pattern, re.I)
            indices = [i for i,n in enumerate(self._names) if pattern.fullmatch(n)]
            return [self._unique_keys[i] for i in indices]

        return list(self._unique_keys)  # return a copy

    def values(self, pattern=None):
        """Iterator over the values in this VicarLabel.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            iterator: The values of the matching parameters within this label, in order.
        """

        self._finish_update()

        if pattern:
            pattern = re.compile(pattern, re.I)
            indices = [i for i,n in enumerate(self._names) if pattern.fullmatch(n)]
            return [self._values[i] for i in indices]

        return list(self._values)

    def items(self, pattern=None, unique=True):
        """Iterator over the (key, value) pairs in this label.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

            unique (bool, optional):
                True to return unique keys, in which non-unique names are replaced by
                tuples (name, occurrence). If False, all keys are name strings, and a name
                may appear multiple times.

        Returns:
            iterator:
                The tuples (name, value) of the matching parameter names within this
                label, in order.
        """

        self._finish_update()

        if pattern:
            pattern = re.compile(pattern, re.I)
            indices = [i for i,n in enumerate(self._names) if pattern.fullmatch(n)]
            if unique:
                return [(self._unique_keys[i], self._values[i]) for i in indices]
            else:
                return [(self._names[i], self._values[i]) for i in indices]

        elif unique:
            return list(zip(self._unique_keys, self._values))

        return list(zip(self._names, self._values))

    def args(self, pattern=None):
        """Iterator over the numerical indices of the keywords.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            iterator:
                The indices of the matching parameter names within this label, in order.
        """

        self._finish_update()

        if pattern:
            pattern = re.compile(pattern, re.I)
            return [i for i,n in enumerate(self._names) if pattern.fullmatch(n)]

        return range(self._len)

    ######################################################################################
    # File I/O
    ######################################################################################

    @staticmethod
    def read_label(source, _extra=False):
        """The VICAR label string from the specified data file.

        If an EOL label is present, the content of the extension label is appended to the
        returned string. This can be recognized by a second occurrence of the LBLSIZE
        parameter.

        Parameters:
            source (str, pathlib.Path, or file):
                A path to a VICAR data file or else a file object already opened for
                binary read.
            _extra (bool, optional):
                True to return any extraneous bytes from the end of the data file in
                addition to the label.

        Returns:
            str or (str, bytes): A string or a tuple containing:

            * str: The VICAR label as a character string, with the EOL label appended if
              one is present. The EOL label can be recognized by the presence of a second
              LBLSIZE parameter.
            * bytes: A bytes object containing any extraneous characters at the end of the
              file, included if `_extra` is True.

        Raises:
            OSError: If the referenced file could not be read.
            VicarError: If the referenced file does not conform to the VICAR standard.
        """

        if isinstance(source, io.IOBase):
            f = source
            filepath = f.name
            close_when_done = False
        else:
            filepath = pathlib.Path(source)
            f = filepath.open('rb')
            close_when_done = True

        try:
            # Read the beginning of the VICAR file to get the label size
            f.seek(0)
            snippet = f.read(40).decode('latin8')
            match = _LBLSIZE_PATTERN.match(snippet)
            if not match:       # pragma: no cover
                raise VicarError('Missing LBLSIZE keyword in file ' + str(filepath))

            lblsize = int(match.group(1))

            # Read the top VICAR label
            f.seek(0)
            label = f.read(lblsize).decode('latin8')
            label = label.partition('\0')[0]

            # Parse
            ldict = VicarLabel(label, strict=False)

            # Figure out the distance to the EOL label
            recsize = ldict['RECSIZE']
            nlb = ldict.get('NLB', 0)
            # N2*N3 is simpler but there are files where these values aren't right
            if ldict['ORG'] == 'BIP':           # pragma: no cover
                data_recs = ldict['NL'] * ldict['NS']
            else:
                data_recs = ldict['NL'] * ldict['NB']
            skip = lblsize + recsize * (nlb + data_recs)
            f.seek(skip)

            # Try to read the EOF label
            snippet = str(f.read(40).decode('latin8'))
            match = _LBLSIZE_PATTERN.match(snippet)
            if match:
                eolsize = int(match.group(1))
                f.seek(skip)
                eol = f.read(eolsize).decode('latin8')
                eol = eol.partition('\0')[0]

                if not label.endswith(' '):     # pragma: no cover
                    label += '  '

                label += eol
            else:
                f.seek(skip)

            # Check for extraneous bytes
            if _extra:
                return (label, f.read())

            return label

        finally:
            if close_when_done:
                f.close()

    @staticmethod
    def from_file(filepath):
        """A new VicarLabel object derived from the given VICAR data file.

        Parameters:
            filepath (str or pathlib.Path): Path to a VICAR data file.

        Returns:
            VicarLabel: VicarLabel object read from file.
        """

        return VicarLabel(source=filepath)

    def write_label(self, filepath=None):
        """Replace the label in the selected VICAR file with this label content.

        Parameters:
            filepath (str or pathlib.Path, optional):
                Optional path of the existing file to write. If not provided, the value of
                this object's filepath attribute is used.

        Note:
            This method modifies the file without first creating a backup, so it should be
            used with caution.
        """

        if not filepath:
            filepath = self._filepath

        if not filepath:
            raise ValueError('file path is missing')

        self._finish_update()

        with self._filepath.open('r+b') as f:

            snippet = f.read(40).decode('latin8')
            match = _LBLSIZE_PATTERN.match(snippet)
            if not match:       # pragma: no cover
                raise VicarError('Missing LBLSIZE keyword in file ' + str(self._filepath))

            lblsize = int(match.group(1))
            self['LBLSIZE'] = lblsize

            # Update the header
            labels = self.export(resize=False)
            f.seek(0)
            f.write(labels[0].encode('latin8'))

            # Update the EOL label, possibly truncating the file
            recsize = self['RECSIZE']
            nlb = self.get('NLB', 0)
            n2 = self['N2']
            n3 = self['N3']
            skip = lblsize + recsize * (nlb + n2*n3)
            f.seek(skip)
            f.write(labels[1].encode('latin8'))
            f.truncate()

    ######################################################################################
    # Other Utilities
    ######################################################################################

    def _set_n321(self, n3, n2, n1):
        """Set the values of N1, N2, N3.

        NB, NL, and NS will be derived from these, depending on the ORG.

        Parameters:
            n3 (int): Value for N3.
            n2 (int): Value for N2.
            n1 (int): Value for N1.
        """

        (self['N1'], self['N2'], self['N3']) = (n1, n2, n3)
        self._nbls_from_n123()

    def _set_nbls(self, nb, nl, ns):
        """Set the values of NB, NL, NS.

        N1, N2, and N3 will be derived from these, depending on the ORG.

        Parameters:
            nb (int): Value for NB.
            nl (int): Value for NL.
            ns (int): Value for NS.
        """

        (self['NB'], self['NL'], self['NS']) = (nb, nl, ns)
        self._n123_from_nbls()

    def _n123_from_nbls(self):
        """Fill in the N1, N2, N3 parameters given values of NB, NL, NS and ORG."""

        if self['ORG'] == 'BSQ':
            (self['N1'], self['N2'], self['N3']) = (self['NS'], self['NL'], self['NB'])
        elif self['ORG'] == 'BIL':
            (self['N1'], self['N2'], self['N3']) = (self['NS'], self['NB'], self['NL'])
        else:   # == 'BIP'
            (self['N1'], self['N2'], self['N3']) = (self['NB'], self['NS'], self['NL'])

    def _nbls_from_n123(self):
        """Fill in the NB, NL, NS parameters given values of N1, N2, N3 and ORG."""

        if self['ORG'] == 'BSQ':
            (self['NS'], self['NL'], self['NB']) = (self['N1'], self['N2'], self['N3'])
        elif self['ORG'] == 'BIL':
            (self['NS'], self['NB'], self['NL']) = (self['N1'], self['N2'], self['N3'])
        else:   # == 'BIP'
            (self['NB'], self['NS'], self['NL']) = (self['N1'], self['N2'], self['N3'])

##########################################################################################
