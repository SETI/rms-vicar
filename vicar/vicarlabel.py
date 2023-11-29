##########################################################################################
# vicar/vicarlabel.py
##########################################################################################
""""Class to support accessing, reading, and modifying VICAR labels."""

import copy
import io
import numbers
import os
import pathlib
import re
import sys

from collections import namedtuple
from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR

_NAME = re.compile(r'[A-Z][A-Z0-9_]{0,31}$')
_LBLSIZE = re.compile(r'LBLSIZE *= *(\d+)')

_ValueFormat = namedtuple('_ValueFormat', ['fmt', 'name_blanks', 'val_blanks',
                                           'sep_blanks', 'listfmts'])
_ListFormat  = namedtuple('_ListFormat',  ['fmt', 'blanks_before', 'blanks_after'])

# [(sys.byteorder,sys.platform)] -> HOST
_HOST_DICT = {('big'   , 'sunos3'): 'SUN-3',
              ('big'   , 'sunos4'): 'SUN-4',
              ('big'   , 'sunos5'): 'SUN-SOLR',
              ('little', 'sunos5'): 'X86-LINUX',
              ('big'   , 'darwin'): 'MAC-OSX',
              ('little', 'darwin'): 'MAC-OSX',
              ('little', 'linux2'): 'X86-LINUX',
              ('little', 'linux3'): 'X86-LINUX',
              ('little', 'linux' ): 'X86-LINUX',
              ('little', 'win32' ): 'WIN-XP'     }

try:
    _HOST = _HOST_DICT[(sys.byteorder, sys.platform)]
except KeyError:                # pragma: no cover
    if sys.platform.startswith('linux'):
        _HOST = 'X86-LINUX'     # could be "linux4" I guess
    else:
        _HOST = sys.platform.upper()

# [sys.byteorder] -> INTFMT, REALFMT
_INTFMT_DICT  = {'little': 'LOW'  , 'big': 'HIGH'}
_REALFMT_DICT = {'little': 'RIEEE', 'big': 'IEEE'}

# Required keywords, default values
_REQUIRED = [('LBLSIZE' , 0,     ),
             ('FORMAT'  , 'BYTE' ),     # Guess
             ('TYPE'    , 'IMAGE'),     # Guess
             ('BUFSIZ'  , 20480  ),     # Always ignored
             ('DIM'     , 3      ),     # Always
             ('EOL'     , 0      ),
             ('RECSIZE' , 0      ),
             ('ORG'     , 'BSQ'  ),
             ('NL'      , 0      ),
             ('NS'      , 0      ),
             ('NB'      , 0      ),
             ('N1'      , 0      ),
             ('N2'      , 0      ),
             ('N3'      , 0      ),
             ('N4'      , 0      ),     # Always
             ('NBB'     , 0      ),
             ('NLB'     , 0      ),
             ('HOST'    , _HOST  ),
             ('INTFMT'  , _INTFMT_DICT [sys.byteorder]),
             ('REALFMT' , _REALFMT_DICT[sys.byteorder]),
             ('BHOST'   , _HOST  ),
             ('BINTFMT' , _INTFMT_DICT [sys.byteorder]),
             ('BREALFMT', _REALFMT_DICT[sys.byteorder]),
             ('BLTYPE'  , ''),]
_REQUIRED_NAMES = set([t[0] for t in _REQUIRED])

_LBLSIZE_WIDTH = 16     # fixed space between "LBLSIZE=" and the next parameter name

_VALID_VALUES = {
    'FORMAT'  : {'BYTE', 'HALF', 'FULL', 'REAL', 'DOUB', 'COMP',
                 'WORD', 'LONG', 'COMPLEX'},
    'ORG'     : {'BSQ', 'BIL', 'BIP'},
    'INTFMT'  : {'HIGH', 'LOW'},
    'REALFMT' : {'IEEE', 'RIEEE', 'VAX'},
    'BINTFMT' : {'HIGH', 'LOW'},
    'BREALFMT': {'IEEE', 'RIEEE', 'VAX'},
    'DIM'     : {3},
    'EOL'     : {0, 1},
    'N4'      : {0},
}

_REQUIRED_INTS = {'LBLSIZE', 'RECSIZE', 'NL', 'NS', 'NB', 'N1', 'N2', 'N3', 'NBB', 'NLB'}


class VicarError(ValueError):
    pass


class VicarLabel():
    """Class to support accessing, reading, modifying, and writing VICAR labels."""

    def __init__(self, source=None):
        """Constructor

        Input:
            source      the path to a VICAR data file, a VICAR label text string or a list
                        of tuples. If no input is provided, a VicarLabel is returned
                        containing only the mandatory parameters with default values.

        A file path can be represented by either a string or a pathlib.Path object.

        If a list of tuples is provided, each tuple must contain a parameter name and a
        value, where the value is represented by an int, float, string, or list.

        Optional formatting can be provided if a user wants additional control over how
        the associated label string will be formatted. The tuple contains up to six values
        in total:
            (name, value[, format][[[, name_blanks], val_blanks], sep_blanks])
        The name and value are required. Optional subsequent items are:
            format          a format string, e.g., "%+7d" or "%7.3f".
            name_blanks     number of blank characters after the name and before the
                            equal sign; zero is the default.
            val_blanks      number of blank characters after the equal sign and before
                            the value; zero is the default.
            sep_blanks      number of blanks after the value and before the next label
                            parameter or the label's end; a default value of zero means
                            that the standard padding (two blanks) will be used when the
                            text string is generated.

        If the value is a list, then each item in the list must be either a parameter
        value (int, float, or string) or else a tuple of up to four values:
            (value[, format][[, blanks_before], blanks_after])
        After the value, the optional items are:
            format          a format string, e.g., "%+07d", "%12.3e" or "%.4f".
            blanks_before   the number of blanks before the value, after the left
                            parenthesis or comma; zero is the default.
            blanks_after    the number of blanks after the value and before the next
                            comma or the right parenthesis; zero is the default.
        """

        # Interpret the input
        if not source:
            self._filepath = None
            params = []
        elif isinstance(source, list):
            self._filepath = None
            params = source
        elif isinstance(source, str):
            if os.path.exists(source) or '=' not in source:
                self._filepath = pathlib.Path(source)
                label = VicarLabel.read_label(self._filepath)
                params = _LABEL_GRAMMAR.parse_string(label).as_list()
            else:
                self._filepath = None
                params = _LABEL_GRAMMAR.parse_string(source).as_list()
        else:
            self._filepath = pathlib.Path(source)
            label = VicarLabel.read_label(self._filepath)
            params = _LABEL_GRAMMAR.parse_string(label).as_list()

        # Insert a missing LBLSIZE or move it to the front if necessary
        names = [t[0] for t in params]
        if 'LBLSIZE' not in names:
            params = _REQUIRED[:1] + params
        elif names[0] != 'LBLSIZE':
            k = names.index('LBLSIZE')
            tuple_ = params.pop(k)
            params = [tuple_] + params

        # Insert any other required parameters at the end
        names = set(t[0] for t in params)
        req_params = []
        for tuple_ in _REQUIRED[1:]:
            name = tuple_[0]
            if name not in names:
                req_params.append(tuple_)

        params += req_params

        # Extract names, values, formats in correct order
        names = [t[0] for t in params]
        values = []
        formats = []
        name_set = set()
        for tuple_ in params:
            (value, valfmt) = VicarLabel._interpret_value_format(tuple_[1:])

            # Check types and values of required parameters
            name = tuple_[0]
            is_first = tuple_[0] not in name_set
            name_set.add(name)
            VicarLabel._check_type(name, value, is_first)

            values.append(value)
            formats.append(valfmt)

        self._update(names, values, formats)

    def _update(self, names, values, formats):
        """Internal method to define or re-define the label's content."""

        for name in names:
            if not VicarLabel._validate_name(name):
                raise VicarError('Invalid VICAR parameter name: ' + repr(name))

        for value in values:
            if not VicarLabel._validate_value(value):
                raise VicarError('Invalid VICAR parameter value: ' + repr(value))

        self._names = names
        self._values = values
        self._formats = formats
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

    @staticmethod
    def _validate_value(value):
        """True if this is a valid value for a VICAR label parameter."""

        if isinstance(value, numbers.Real):
            return True

        if isinstance(value, str):
            return value.isascii()

        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                return False

            if isinstance(value[0], numbers.Integral):
                types = numbers.Integral
            elif isinstance(value[0], numbers.Real):
                types = numbers.Real
            elif isinstance(value[0], str):
                types = str
            else:
                return False

            return all(isinstance(v, types) for v in value[1:])

        return False

    @staticmethod
    def _validate_name(name):
        """True if this is a valid name for a VICAR label parameter."""

        return bool(_NAME.match(name))

    @staticmethod
    def _check_type(name, value, is_first):
        """Raise an exception for an invalid value of a required VICAR parameter."""

        if name in _VALID_VALUES:
            # Only the first occurrence of these is constrained; for example,
            # ORG='ROW' exists in some files, but only after ORG='BSQ'.
            if value not in _VALID_VALUES[name] and is_first:
                raise VicarError(f'Invalid value for {name}: {repr(value)}; '
                                 f'must be in {_VALID_VALUES[name]}')
        elif name in _REQUIRED_INTS:
            # This constraint applies to every occurrence, not just the first
            if not isinstance(value, numbers.Integral) or value < 0:
                raise VicarError(f'Invalid value for {name}: {repr(value)}; '
                                 f'must be a non-negative integer')

    @staticmethod
    def _interpret_value_format(tuple_):
        """Get the value and optional format from a (value, optional format info) tuple.
        """

        # If this is not a tuple, the input is a standalone value with no format
        if not isinstance(tuple_, tuple):
            tuple_ = (tuple_,)

        # If this parameter value is a list, interpret its values and formatting
        if isinstance(tuple_[0], list):
            value = []
            listfmts = []
            for subval in tuple_[0]:

                # Tuple case: (value[, format][[, blanks_before], blanks_after])
                if isinstance(subval, tuple):
                    value.append(subval[0])

                    if isinstance(subval[1], str):
                        listfmt = subval[1]
                        blanks = list(subval[2:])
                    else:
                        listfmt = ''
                        blanks = list(subval[1:])

                    while len(blanks) < 2:
                        blanks = [0] + blanks

                    listfmt = _ListFormat(listfmt, *blanks)
                else:
                    value.append(subval)
                    listfmt = None

                listfmts.append(listfmt)

            if not any(listfmts):
                listfmts = []

        # Otherwise, the value is easy and there are no list formats
        else:
            value = tuple_[0]
            listfmts = []

        # Interpret the rest of the tuple
        if len(tuple_) > 1:
            if isinstance(tuple_[1], str):
                fmt = tuple_[1]
                blanks = list(tuple_[2:])
            else:
                fmt = ''
                blanks = list(tuple_[1:])

            while len(blanks) < 3:
                blanks = [0] + blanks

            valfmt = _ValueFormat(fmt, *blanks, listfmts)

        elif listfmts:
            valfmt = _ValueFormat('', 0, 0, 0, listfmts)

        else:
            valfmt = None

        return (value, valfmt)

    ########################################

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, value):
        if value:
            self._filepath = pathlib.Path(value)
        else:
            self._filepath = None

    def copy(self):
        """An independent (deep) copy of this VicarLabel."""

        return copy.deepcopy(self)

    def __eq__(self, other):
        """VicarLabels are equal if they have the same parameter names in the same order.
        Formatting and filepath are ignored.
        """
        return (self._names == other._names
                and self._values == other._values)

    ########################################

    def append(self, source):
        """Insert the content of a second VICAR label into this object.

        Input:
            source      a VICAR label text string or a list of tuples.

        If a list of tuples is provided, each tuple must contain a parameter name and a
        value, where the value is represented by an int, float, string, or list.

        Optional formatting can be provided if a user wants additional control over how
        the associated label string will be formatted. The tuple contains up to six values
        in total:
            (name, value[, format][[[, name_blanks], val_blanks], sep_blanks])
        The name and value are required. Optional subsequent items are:
            format          a format string, e.g., "%+7d" or "%7.3f".
            name_blanks     number of blank characters after the name and before the
                            equal sign; zero is the default.
            val_blanks      number of blank characters after the equal sign and before
                            the value; zero is the default.
            sep_blanks      number of blanks after the value and before the next label
                            parameter or the label's end; default 2.

        If the value is a list, then each item in the list must be either a parameter
        value (int, float, or string) or else a tuple of up to four values:
            (value[, format][[, blanks_before], blanks_after])
        After the value, the optional items are:
            format          a format string, e.g., "%+07d", "%12.3e" or "%.4f".
            blanks_before   the number of blanks before the value, after the left
                            parenthesis or comma; zero is the default.
            blanks_after    the number of blanks after the value and before the next
                            comma or the right parenthesis; zero is the default.
        """

        # Convert from string to list of tuples
        if not isinstance(source, list):
            source = _LABEL_GRAMMAR.parse_string(source).as_list()

        # Extract names, values, formats in order
        names = [t[0] for t in source]
        values = []
        formats = []
        for tuple_ in source:
            (value, valfmt) = VicarLabel._interpret_value_format(tuple_[1:])
            values.append(value)
            formats.append(valfmt)

        self._update(self._names + names, self._values + values, self._formats + formats)

    ########################################

    def reorder(self, *keys):
        """Re-order one or more specified parameters inside this object.

        Input: two or more parameter names or (name, occurrence) keys.

        The first key is left in place, and subsequent keys are positioned after it in the
        order given. Use "" in front of the first key if you want the listed keys to be
        first.
        """

        move_to_front = (keys[0] == '')
        if move_to_front:
            keys = keys[1:]

        order = [self.arg(k) for k in keys]
        order_set = set(order)
        if len(order) != len(order_set):
            raise ValueError('Invalid new index order')

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
    # Shape methods
    ######################################################################################

    def _set_n321(self, n3, n2, n1):
        """Set the values of N1, N2, N3."""

        (self['N1'], self['N2'], self['N3']) = (n1, n2, n3)
        self._nbls_from_n123()

    def _set_nbls(self, nb, nl, ns):
        """Set the values of NB, NL, NS."""

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

    ######################################################################################
    # Indexing methods
    ######################################################################################

    def __len__(self):
        """The number of keywords in the VICAR label."""

        return self._len

    ########################################

    def __getitem__(self, key):
        """Retrieve the value of the VICAR parameter defined by this name, (name,
        occurrence), or numeric index.

        If a name appears multiple times in the label, this returns the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.

        Append a "+" to a name to retrieve a list containing all the values of that
        parameter name.
        """

        if isinstance(key, numbers.Integral):
            return self._values[key]            # IndexError if out of range

        try:
            indx = self._key_index[key][0]      # first if more than one
        except KeyError as e:
            error = e
        else:
            return self._values[indx]

        # Check for IndexError
        if (isinstance(key, tuple) and isinstance(key[0], str)
                                   and isinstance(key[1], numbers.Integral)
                                   and key[0] in self._key_index):
            raise IndexError(key[0] + ' index out of range')

        # Handle "+" suffix
        if not isinstance(key, str):
            raise error

        if key.endswith('+'):
            name = key[:-1]
            if name in self._key_index:
                return [self._values[i] for i in self._key_index[name]]

        raise error

    ########################################

    def get(self, key, default):
        """The value of a VICAR parameter defined by this name, (name, occurrence), or
        numeric index. If the key is missing, return the default value.

        If a name appears multiple times in the label, this returns the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.
        """

        try:
            return self[key]
        except Exception:
            return default

    ########################################

    def arg(self, key):
        """The numerical index of the item in the VICAR label defined by this name, (name,
        occurrence), or numeric index.

        If a name appears multiple times in the label, this returns the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.
        """

        if isinstance(key, numbers.Integral):
            if key < 0:
                key += self._len
            if key >= 0 and key < self._len:
                return key
            raise IndexError('list index out of range')

        try:
            return self._key_index[key][0]
        except KeyError as e:
            error = e

        # Check for IndexError instead of KeyError
        if (isinstance(key, tuple) and isinstance(key[0], str)
                                   and isinstance(key[1], numbers.Integral)
                                   and key[0] in self._key_index):
            raise IndexError(key[0] + ' index out of range')

        raise error

    ########################################

    def __setitem__(self, key, value):
        """Set the value of the VICAR parameter defined by this name, (name, occurrence),
        or numeric index. If the parameter is not currently found in the label, create a
        new one.

        If a name appears multiple times in the label, this sets the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.

        Append a "+" to a name to append a new "name=value" pair the label, even if that
        name already appears.
        """

        # Handle a numeric index
        if isinstance(key, numbers.Integral):

            # Handle an input with embedded formatting info
            (value, valfmt) = VicarLabel._interpret_value_format(value)
            if not VicarLabel._validate_value(value):
                raise VicarError('Invalid VICAR parameter value: ' + repr(value))

            name = self._names[key]
            is_first = self._key_index[name][0] == key
            VicarLabel._check_type(name, value, is_first)

            # Default to the pre-existing format if it works
            if not valfmt:
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

            self._values[key] = value
            self._formats[key] = valfmt
            return

        # Handle a string or tuple index recursively
        try:
            indx = self._key_index[key][0]
        except (KeyError, TypeError):
            pass
        else:
            self.__setitem__(indx, value)
            return

        # Handle a new name or append to a name
        if not isinstance(key, str):
            raise VicarError('Invalid VICAR parameter name: ' + repr(key))

        if key.endswith('+'):
            key = key[:-1]

        (value, valfmt) = VicarLabel._interpret_value_format(value)
        VicarLabel._check_type(key, value, is_first=False)

        names = self._names + [key]
        values = self._values + [value]
        formats = self._formats + [valfmt]

        self._update(names, values, formats)

    ########################################

    def __delitem__(self, key):
        """Delete the value of the VICAR parameter defined by this name, (name,
        occurrence), or numeric index.

        If a name appears multiple times in the label, this deletes the first occurrence.
        Use the tuple (name, n) to return later values, where n = 0, 1, 2 ... to index
        from the first occurrence, or n = -1, -2, ... to index from the last.
        """

        if isinstance(key, numbers.Integral):

            name = self._names[key]
            if name in _REQUIRED_NAMES:
                is_first = self._key_index[name][0] == key
                if is_first:
                    raise VicarError('The first occurrence of {name} cannot be deleted')

            names = list(self._names)
            values = list(self._values)
            formats = list(self._formats)

            names.pop(key)
            values.pop(key)
            formats.pop(key)

            self._update(names, values, formats)
            return

        indx = self._key_index[key][0]      # raise KeyError on failure
        self.__delitem__(indx)

    ########################################

    def __contains__(self, key):
        """True if the given key exists in the VICAR label."""

        return (key in self._key_index)

    ######################################################################################
    # String methods
    ######################################################################################

    def value_str(self, key):
        """The value of the given parameter as it will appear in the label."""

        def _scalar_str(value, fmt=''):

            if fmt:
                return fmt % value

            if isinstance(value, numbers.Integral):
                return str(value)
            if isinstance(value, numbers.Real):
                return _float_str(value)

            return "'" + value.replace("'", "''") + "'"

        def _float_str(value):
            """Format a float using a reasonable set of digits; avoid "00000" or "99999".
            """

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

        #### Active code...

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

        If pad is True, the string will always end with at least one blank character.
        """

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

        Input:
            resize      if True, LBLSIZE will be modified to accommodate the new content.
                        Otherwise, the current value of LBLSIZE will be preserved and any
                        overflow content will be placed into an EOL label. In this case, a
                        second LBLSIZE parameter will mark the starting location of this
                        label.
        """

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
        """Two strings representing the contents of a VICAR label in a data file.

        The first string contains the VICAR label at the top of the file, as constrained
        by the internal values of LBLSIZE and RECSIZE. The second is the content of the
        EOL label, which is either an empty string or label text beginning with a second
        value of LBLSIZE. Each string is padded with null characters to the full length
        specified by LBLSIZE.

        Note that the returned strings must be encoded as "latin8" bytes before writing
        into a file.
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
        """This VicarLabel content as a string.

        Input:
            start       index or key of the first parameter index; default 0.
            stop        index or key just after the last parameter index; omit to include
                        all remaining VICAR parameters in the returned string.
            sep         optional characters to insert before the second LBLSIZE, if any.
        """

        start = self.arg(start)
        stop = self._len if not stop else min(self._len, self.arg(stop))

        label = []
        for k in range(start, stop):
            name_value = self.name_value_str(k, pad=True)

            # Add optional separator before a second LBLSIZE
            if sep and k > 0 and self._names[k] == 'LBLSIZE':
                label.append(sep)

            label.append(name_value)

        return ''.join(label)

    def __str__(self):
        return self.as_string()

    def __repr__(self):
        return 'VicarLabel("""' + self.as_string(sep='\n\n') + '""")'

    ######################################################################################
    # Iterators (mostly just lists)
    ######################################################################################

    def __iter__(self):
        """Iterator over the unique names or (name, occurrence) pairs in the label."""

        self._counter = 0
        return self

    def __next__(self):

        i = self._counter
        if i >= self._len:
            raise StopIteration

        self._counter += 1
        return self._unique_keys[i]

    def names(self, pattern=None):
        """Iterator over the parameter name strings in this VicarLabel.

        Implemented as a simple list.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
        """

        if pattern:
            pattern = re.compile(pattern, re.I)
            return [n for n in self._names if pattern.fullmatch(n)]

        return list(self._names)

    def keys(self, pattern=None):
        """Iterator over the label keys. The key is the parameter name if it is unique or
        (name, occurrence number) otherwise.

        Implemented as a simple list.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
        """

        if pattern:
            pattern = re.compile(pattern, re.I)
            indices = [i for i,n in enumerate(self._names) if pattern.fullmatch(n)]
            return [self._unique_keys[i] for i in indices]

        return list(self._unique_keys)

    def values(self, pattern=None):
        """Iterator over the values in this VicarLabel.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
        """

        if pattern:
            pattern = re.compile(pattern, re.I)
            indices = [i for i,n in enumerate(self._names) if pattern.fullmatch(n)]
            return [self._values[i] for i in indices]

        return list(self._values)

    def items(self, pattern=None, unique=True):
        """Iterator over the (key, value) pairs in this VicarLabel.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
            unique      True to return unique keys, in which non-unique names are replaced
                        by tuples (name, occurrence). If False, all keys are name strings,
                        and a string may appear multiple times.
        """

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
        """Iterator over the numerical indices of the keywords."""

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

        If an EOL label is present, its content is appended to the returned string. This
        can be recognized by a second occurrence of the LBLSIZE parameter.

        Input:
            source      path to a VICAR data file, represented by either a string or a
                        pathlib.Path object, or else a file object already opened for
                        binary read.
            _extra      True to return any extraneous bytes from the end of the data file
                        in addition to the label.

        Return          text or (text, extra)
            text        the VICAR label as a character string, with the EOL label appended
                        if one is present. The EOL label can be recognized by the presence
                        of a second LBLSIZE parameter.
            extra       a bytes object containing any extraneous characters at the end of
                        the file; included if input _extra is True.
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
            match = _LBLSIZE.match(snippet)
            if not match:       # pragma: no cover
                raise VicarError('Missing LBLSIZE keyword in file ' + str(filepath))

            lblsize = int(match.group(1))

            # Read the top VICAR label
            f.seek(0)
            label = f.read(lblsize).decode('latin8')
            label = label.partition('\0')[0]

            # Parse
            ldict = VicarLabel(label)

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
            match = _LBLSIZE.match(snippet)
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

        Input:
            filepath    path to a VICAR data file, represented by either a string or a
                        pathlib.Path object.
        """

        return VicarLabel(source=filepath)

    def write_label(self, filepath=None):
        """Replace the label in the selected VICAR file with this label content.

        Note that this method modifies the file without first creating a backup, so it
        should be used with caution.

        Input:
            filepath    optional path of the existing file to write. If not provided, the
                        value of this object's filepath attribute is used.
        """

        if not filepath:
            filepath = self._filepath

        if not self._filepath:
            raise ValueError('file path is missing')

        with self._filepath.open('r+b') as f:

            snippet = f.read(40).decode('latin8')
            match = _LBLSIZE.match(snippet)
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

##########################################################################################
