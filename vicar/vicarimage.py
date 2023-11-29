##########################################################################################
# vicar/vicarimage.py
##########################################################################################
"""Class to support accessing, reading, and modifying VICAR image files."""

import copy
import numbers
import numpy as np
import pathlib
import sys
import vax
import warnings

try:
    from _version import __version__
except ImportError:
    __version__ = 'Version unspecified'

from vicar.vicarlabel import VicarLabel, VicarError, _HOST

##########################################################################################
# Set of keywords that the user cannot modify
##########################################################################################

_IMMUTABLE = set(['LBLSIZE' ,
                  'FORMAT'  ,
                  'TYPE'    ,
                  'DIM'     ,
                  'EOL'     ,
                  'RECSIZE' ,
                  'ORG'     ,
                  'NL'      ,
                  'NS'      ,
                  'NB'      ,
                  'N1'      ,
                  'N2'      ,
                  'N3'      ,
                  'N4'      ,
                  'NBB'     ,
                  'NLB'     ,
                  'INTFMT'  ,
                  'REALFMT' ,
                  'BINTFMT' ,
                  'BREALFMT'])

##########################################################################################
# Utilities
##########################################################################################

# [FORMAT] -> dtype
_DTYPE_FROM_FORMAT = {'BYTE': 'u1',
                      'HALF': 'i2',
                      'FULL': 'i4',
                      'REAL': 'f4',
                      'DOUB': 'f8',
                      'COMP': 'c8',
                      'WORD': 'i2',
                      'LONG': 'i4',
                      'COMPLEX': 'c8'}

# [dtype.kind + str(dtype.itemsize)] -> (FORMAT, isint)
_FORMAT_FROM_DTYPE = {'u1': ('BYTE', True ),
                      'i2': ('HALF', True ),
                      'i4': ('FULL', True ),
                      'f4': ('REAL', False),
                      'f8': ('DOUB', False),
                      'c8': ('COMP', False)}

def _intfmt(x):
    if isinstance(x, np.ndarray):
        if x.dtype.byteorder == '<':    # pragma: no cover
            return 'LOW'
        if x.dtype.byteorder == '>':    # pragma: no cover
            return 'HIGH'

    return 'LOW' if sys.byteorder == 'little' else 'HIGH'

def _realfmt(x):
    if isinstance(x, np.ndarray):
        if x.dtype.byteorder == '>':    # pragma: no cover
            return 'IEEE'
        if x.dtype.byteorder == '<':    # pragma: no cover
            return 'RIEEE'

    return 'RIEEE' if sys.byteorder == 'little' else 'IEEE'

def _format_isint(x):
    try:
        key = x.dtype.kind + str(x.itemsize)
        return _FORMAT_FROM_DTYPE[key]
    except KeyError:
        raise VicarError(f'array dtype "{x.dtype}" is not supported by VICAR')

def _check_array_vs_prefix(array, prefix):
    """Raise an exception if the given image array and prefix byte array are not
    compatible.
    """

    if array is not None and array.ndim != 3:
        raise VicarError(f'array shape {array.shape} is not 2-D or 3-D')

    if prefix is not None and prefix.ndim != 3:
        raise VicarError(f'shape of prefix bytes {prefix.shape} is not 2-D or 3-D')

    if array is None or prefix is None:
        return

    if array.shape[:-1] != prefix.shape[:-1]:
        raise VicarError('image and prefix bytes have incompatible shapes: '
                         f'{array.shape}, {prefix.shape}')

    (format1, isint1) = _format_isint(array)
    if isint1:
        intfmt1 = _intfmt(array)
    else:
        realfmt1 = _realfmt(array)

    (format2, isint2) = _format_isint(prefix)
    if isint2:
        intfmt2 = _intfmt(prefix)
    else:
        realfmt2 = _realfmt(prefix)

    if isint1 and isint2:
        if format1 != 'BYTE' and format2 != 'BYTE' and intfmt1 != intfmt2:
            raise VicarError('prefix and array formats are incompatible: '
                             f'{intfmt1}, {intfmt2}')
    if not isint1 and not isint2:
        if realfmt1 != realfmt2:
            raise VicarError('prefix and array formats are incompatible: '
                             f'{realfmt1}, {realfmt2}')

##########################################################################################
# Class VicarImage
##########################################################################################

class VicarImage():
    """This class defines the contents of a VICAR data file. It supports methods for
    reading and writing files and for accessing header information.
    """

    def __init__(self, source=None, array=None, *, prefix=None, binheader=None):
        """Constructor for a VicarImage object.

        Input:
            source      optional path to a VICAR data file as a string or a pathlib.Path
                        object, or else a VicarLabel object.
            array       optional data array for this object. If the source is a file path,
                        this array will override that in the file.
            prefix      optional prefix bytes for this object. If the source is a file
                        path, this value will override that in the file. To remove the
                        prefix array found in the file, use prefix=[].
            binheader   optional binary header for this data file. If the source is a
                        file path, this value will override that in the file. To remove
                        the binheader found in the file, use binheader=b''.
        """

        self._filepath = None

        if not source:
            self._label = VicarLabel([])
        elif isinstance(source, VicarLabel):
            self._label = source
        else:
            self._filepath = pathlib.Path(source)
            info = VicarImage._read_file(self.filepath, extraneous='ignore')
            (self._label, array1, prefix1, binheader1) = info

            if array is None:
                array = array1
            if prefix is None:
                prefix = prefix1
            if binheader is None:
                binheader = binheader1

        # Validate array, prefix, and binheader using setters
        self._array = None
        self._prefix = None
        self._binheader = None

        self.array = array
        self.prefix = prefix
        self.binheader = binheader

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, value):
        if value is None:
            self._filepath = None
        else:
            self._filepath = pathlib.Path(value)

    @property
    def label(self):
        """The VicarLabel object."""
        return self._label

    @property
    def array2d(self):
        """The array object as 2-D."""

        if self._array is None:
            return None
        if self._array.shape[0] != 1:
            raise VicarError(f'VICAR array shape {self._array.shape} is not 2-D')
        return self._array[0]

    @property
    def data_2d(self):
        """The array object as 2-D; DEPRECATED name."""
        return self.array2d

    @property
    def array3d(self):
        """The array object as 3-D."""
        return self._array

    @property
    def data_3d(self):
        """The array object as 3-D; DEPRECATED name."""
        return self._array

    @property
    def array(self):
        return self._array

    @array.setter
    def array(self, value):

        if value is None:
            self._array = None
            return

        value = np.asarray(value)
        value = value.reshape((3-value.ndim) * (1,) + value.shape)  # reshape to 3-D
        _check_array_vs_prefix(value, self._prefix)

        recsize = self._label['NBB'] + value.shape[-1] * value.itemsize
        nlb = self._label['NLB']
        if self._binheader is not None:
            width = len(bytes(self._binheader))
            if width % recsize != 0:
                raise VicarError(f'array shape {value.shape} is incompatible with binary '
                                 f'header width {width}')
            nlb = width // recsize

        # Tests passed
        self._array = value
        self._label['HOST'] = _HOST
        self._label['TYPE'] = 'IMAGE'
        (self._label['FORMAT'], isint) = _format_isint(value)
        if isint:
            if value.itemsize > 1:
                self._label['INTFMT'] = _intfmt(value)
        else:
            self._label['REALFMT'] = _realfmt(value)

        self._label['RECSIZE'] = recsize
        self._label['NLB'] = nlb
        self._label._set_n321(*value.shape)

    @property
    def prefix2d(self):
        """The image prefix object as a 2-D array."""

        if self._prefix is None:
            return None
        if self._prefix.shape[0] != 1:
            raise VicarError(f'prefix bytes shape {self._prefix.shape} is not 2-D')
        return self._prefix[0]

    @property
    def prefix_2d(self):
        """The image prefix object as a 2-D array."""
        return self.prefix2d

    @property
    def prefix3d(self):
        """The image prefix object as a 3-D array."""
        return self._prefix

    @property
    def prefix_3d(self):
        """The image prefix object as a 3-D array."""
        return self._prefix

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):

        if value is None:
            nbb = 0
        else:
            value = np.asarray(value)
            if value.size == 0:
                nbb = 0
                value = None
            else:
                value = value.reshape((3-value.ndim) * (1,) + value.shape)
                _check_array_vs_prefix(self._array, value)
                nbb = value.shape[-1] * value.itemsize

        recsize = self['RECSIZE']
        nlb = self['NLB']
        if self._array is not None:
            recsize = self._array.shape[-1] * self._array.itemsize + nbb
            if self._binheader is not None:
                width = len(bytes(self._binheader))
                if width % recsize != 0:
                    raise VicarError(f'new RECSIZE={recsize} is incompatible with binary '
                                     f'header length {width}')
                nlb = width // recsize

        # Tests passed
        self._prefix = value
        self._label['NBB'] = nbb
        self._label['NLB'] = nlb
        self._label['RECSIZE'] = recsize

        if value is not None:
            self._label['HOST'] = _HOST
            (fmt, isint) = _format_isint(value)

            # Prefix defines attributes left undefined by array
            if self._array is None:
                self._label['FORMAT'] = fmt

            if isint:
                if self._array is None or self._array.dtype.kind in 'fc':
                    if value.itemsize > 1:
                        self._label['INTFMT'] = _intfmt(value)
            else:
                if self._array is None or self._array.dtype.kind in 'ui':
                    self._label['REALFMT'] = _realfmt(value)

    @property
    def binheader(self):
        """The binary header as an array or bytes object."""
        return self._binheader

    @binheader.setter
    def binheader(self, value):

        if value is None:
            self._binheader = None
            self._label['NLB'] = 0
            return

        nlb = self._label['NLB']
        width = len(bytes(value))
        if self._array is not None:
            recsize = self._label['RECSIZE']
            if width % recsize != 0:
                raise VicarError(f'binary header length {width} is incompatible with '
                                 f'RECSIZE={recsize}')
            nlb = width // recsize

        # Tests passed
        self._binheader = None if width == 0 else value
        self._label['BHOST'] = _HOST
        self._label['NLB'] = nlb

        if isinstance(value, np.ndarray):
            if value.dtype.kind in 'cf':
                self._label['BREALFMT'] = _realfmt(value)
            elif value.dtype.kind in 'ui' and value.dtype.itemsize > 1:
                self._label['BINTFMT'] = _intfmt(value)

    @staticmethod
    def from_file(filepath, extraneous='ignore'):
        """VicarImage object from an existing VICAR image file.

        Input:
            filepath    path to a VICAR data file as a string or a pathlib.Path object.
            extraneous  how to handle the presence of extraneous bytes at the end of the
                        file:
                            "error"     to raise VicarError;
                            "warn"      to raise a UserWarning;
                            "print"     to print a message;
                            "ignore"    to ignore;
                            "include"   to include the extraneous bytes as part of the
                                        return.
        """

        info = VicarImage._read_file(filepath, extraneous=extraneous)
        (label, data, prefix, binheader) = info[:4]
        vim = VicarImage(source=label, array=data, prefix=prefix, binheader=binheader)

        if extraneous == 'include':
            return (vim, info[4])

        return vim

    @staticmethod
    def from_array(array):
        """Returns a VicarImage object given an array.

        Inputs:
            array       the array containing the data to use in the VicarImage
                        object.

        Return:         a VicarImage object.
        """

        return VicarImage(source=[], array=array)

    def binheader_array(self, kind='', size=None):
        """The numbers embedded in a binary header.

        This method is capable of reading ISIS table files when those tables consist
        entirely of a single data format. It uses the FMT_DEFAULT parameter to determine
        dtype, and uses the NR and NC values, if present, to determine the number of rows
        and columns in the table.

        Input:
            kind        optional single-letter code for the data type: u = unsigned int;
                        i = signed int; f = float. If not specified, the kind is inferred
                        from the value of the FMT_DEFAULT parameter.
            size        number of bytes per value. If not provided, it is inferred from
                        the FMT_DEFAULT parameter if present. Otherwise, the default is
                        1 for kind = "u"; 2 for kind = "i"; 4 for kind = "f".
        """

        if self._binheader is None:
            return None

        if isinstance(self._binheader, np.ndarray):
            return self._binheader

        label = self._label

        # Determine kind, size, and dtype
        if not kind:
            dpref = ('>' if label['BREALFMT'] == 'IEEE' else '<')
            dtype = dpref + _DTYPE_FROM_FORMAT[label.get('FMT_DEFAULT', 'REAL')]
            kind = dtype[1]
            size = int(dtype[2:])

        elif kind in 'ui':
            size = size if size else 2 if kind == 'i' else 1
            dpref = ('<' if label['BINTFMT'] == 'LOW' else '>')
            dtype = dpref + kind + str(size)

        else:
            size = size if size else 4
            dpref = ('>' if label['BREALFMT'] == 'IEEE' else '<')
            dtype = dpref + kind +  str(size)

        # Convert the bytes to an array
        values = np.frombuffer(self._binheader, dtype=dtype)

        # Check for table dimensions and them if found
        if 'NR' in label and 'NC' in label:
            nr = label['NR']
            nc = label['NC']
            values = values[:(nr*nc)]
            values = values.reshape(nr,nc)

        # Deal with the possibility of Vax reals
        if kind not in 'ui' and label['BREALFMT'] == 'VAX':
            if size == 8:       # pragma: no cover
                values = vax.from_vax64(values)
            else:
                values = vax.from_vax32(values)

        return values

    def copy(self):
        """An independent (deep) copy of this VicarImage."""

        return copy.deepcopy(self)

    def __eq__(self, other):

        prefix1 = b'' if self._prefix is None else bytes(self._prefix)
        prefix2 = b'' if other._prefix is None else bytes(other._prefix)

        binheader1 = b'' if self._binheader is None else bytes(self._binheader)
        binheader2 = b'' if other._binheader is None else bytes(other._binheader)

        return (self._label == other._label
                and np.all(self._array == other._array)
                and prefix1 == prefix2
                and binheader1 == binheader2)

    ######################################################################################
    # File I/O
    ######################################################################################

    @staticmethod
    def _read_file(filepath, extraneous='ignore'):
        """The VICAR data array, binary header, and prefix bytes from the specified
        data file.

        Input:
            filepath    path to a VICAR data file, represented by either a string or a
                        pathlib.Path object.
            extraneous  how to handle the presence of extraneous bytes at the end of the
                        file:
                            "error"     to raise VicarError;
                            "warn"      to raise a UserWarning;
                            "print"     to print a message;
                            "ignore"    to ignore;
                            "include"   to include the extraneous bytes as part of the
                                        returned tuple.

        Return          (label, data, prefix, binheader[, extra])
            label       the VICAR label of this file as a VicarLabel object.
            data        the data as a 3D array converted to native format.
            prefix      the array prefix bytes as a 3D array of unsigned bytes.
            binheader   the binary header as a bytes object.
            extra       any extraneous bytes at the end of the file as a bytes object,
                        included if input extraneous = "include".
        """

        if extraneous not in ('ignore', 'print', 'warn', 'error', 'include'):
            raise ValueError('invalid input value for extraneous: ' + repr(extraneous))

        filepath = pathlib.Path(filepath)
        with filepath.open('rb') as f:

            # Get the label
            (label, extra) = VicarLabel.read_label(f, _extra=True)

            # Handle extraneous bytes
            if extra:
                if all(c == 0 for c in extra):
                    message = (f'{filepath} has {len(extra)} zero-valued trailing bytes')
                else:       # pragma: no cover
                    message = (f'{filepath} has {len(extra)} trailing bytes')

                if extraneous == 'print':
                    print(message)
                elif extraneous == 'warn':
                    warnings.warn(message)
                elif extraneous == 'error':
                    raise VicarError(message)

            # Extract key label parameters
            ldict = VicarLabel(label)
            lblsize = ldict['LBLSIZE']              # bytes in header
            recsize = ldict['RECSIZE']              # bytes per record
            nlb     = ldict['NLB']                  # records of binary header
            nbb     = ldict['NBB']                  # number of binary prefix bytes
            intfmt  = ldict.get('INTFMT', 'LOW')    # LOW or HIGH
            realfmt = ldict.get('REALFMT', 'VAX')   # IEEE, RIEEE, or VAX
            format_ = ldict['FORMAT']               # BYTE, HALF, FULL, REAL, etc.

            # Read the binary header
            f.seek(lblsize)
            if nlb:
                binheader = f.read(nlb * recsize)
            else:
                binheader = None

            # Read the data and prefix bytes
            ldict._n123_from_nbls()     # Sometimes N1, N2, N3 are wrong
            n2 = ldict['N2']
            n3 = ldict['N3']
            if n2 and n3:
                data = np.frombuffer(f.read(n3 * n2 * recsize), dtype='uint8')
                data = data.reshape(n3, n2, recsize)
            else:
                data = None

        # Separate the prefix bytes from the data
        if nbb and data is not None:
            array = data[:,:,nbb:].copy()
            prefix = data[:,:,:nbb].copy()
        else:
            array = data
            prefix = None

        # Convert the array to native format
        if array is not None:
            dtype = _DTYPE_FROM_FORMAT[format_]
            if dtype[0] in 'ui':
                dtype = ('>' if intfmt == 'HIGH' else '<') + dtype
            else:       # "fc"
                if realfmt == 'VAX':        # pragma: no cover
                    if dtype[-1] == '8':
                        array = vax.from_vax64(array)
                    else:
                        array = vax.from_vax32(array)
                    dtype = '<' + dtype
                else:
                    dtype = ('>' if realfmt == 'IEEE' else '<') + dtype

            array = array.view(dtype=dtype)                     # define actual format
            array = np.asarray(array, dtype='=' + dtype[1:])    # convert to native format

        if extraneous == 'include':
            return (ldict, array, prefix, binheader, extra)

        return (ldict, array, prefix, binheader)

    def write_file(self, filepath=None):
        """Write the VicarImage object into a file.

        Inputs:
            filepath    optional the path of the file to write, as a string or
                        pathlib.Path object. If not specified and this object's filepath
                        attribute is defined, it will write to the file.
        """

        filepath = filepath or self.filepath

        if self._array is None:
            raise VicarError('Image array is missing for ' + str(filepath))

        self.filepath = filepath

        # Open the file for binary write
        with self._filepath.open('wb') as f:

            labels = self._label.export(resize=True)
            f.write(labels[0].encode('latin8'))

            if self._binheader is not None:
                if isinstance(self._binheader, np.ndarray):
                    f.write(self._binheader.data)
                else:
                    f.write(self._binheader)

            if self._prefix is None and self._array is not None:
                f.write(self._array.data)
            else:
                n2 = self._label['N2']
                n3 = self._label['N3']
                nbb = self._label['NBB']
                recsize = self._label['RECSIZE']
                array = np.empty((n3,n2,recsize), dtype='uint8')
                array[:,:,:nbb] = self._prefix.view(dtype='uint8')
                array[:,:,nbb:] = self._array.view(dtype='uint8')
                f.write(array.data)

            f.write(labels[1].encode('latin8'))

    ######################################################################################
    # Public methods inherited from the VicarLabel object
    ######################################################################################

    def __len__(self):
        """The number of keywords in the VICAR label."""

        return self._label._len

    def __getitem__(self, key):
        """Retrieve the value of the VICAR parameter defined by this name, (name,
        occurrence), or numeric index.

        If a name appears multiple times in the label, this returns the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.

        Append a "+" to a name to retrieve a list containing all the values of that
        parameter name.
        """

        return self._label.__getitem__(key)

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

        if isinstance(key, numbers.Integral):
            name = self._label.names()[key]
        elif isinstance(key, tuple):
            name = key[0]
        else:
            name = key

        if name in _IMMUTABLE:
            raise VicarError(f'VICAR parameter {name} cannot be modified')

        self._label.__setitem__(key, value)

    def __delitem__(self, key):
        """Delete the value of the VICAR parameter defined by this name, (name,
        occurrence), or numeric index.

        If a name appears multiple times in the label, this deletes the first occurrence.
        Use the tuple (name, n) to return later values, where n = 0, 1, 2 ... to index
        from the first occurrence, or n = -1, -2, ... to index from the last.
        """

        if isinstance(key, numbers.Integral):
            name = self._label.names()[key]
        elif isinstance(key, tuple):
            name = key[0]
        else:
            name = key

        if name in _IMMUTABLE:
            raise VicarError(f'VICAR parameter {name} cannot be deleted')

        self._label.__delitem__(key)

    def __contains__(self, key):
        """True if the given key exists in the label of this VicarImage."""

        return self._label.__contains__(key)

    def get(self, key, default):
        """The value of a VICAR parameter defined by this name, (name, occurrence), or
        numeric index. If the key is missing, return the default value.

        If a name appears multiple times in the label, this returns the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.
        """

        try:
            return self._label[key]
        except Exception:
            return default

    def arg(self, key):
        """The numerical index of the item in the VICAR label defined by this name, (name,
        occurrence), or numeric index.

        If a name appears multiple times in the label, this returns the value at the first
        occurrence. Use the tuple (name, n) to return later values, where n = 0, 1, 2 ...
        to index from the first occurrence, or n = -1, -2, ... to index from the last.
        """

        return self._label.arg(key)

    def __str__(self):
        return str(self._label)

    def __repr__(self):
        return 'VicarImage("""' + self._label.as_string(sep='\n\n') + '""")'

    def __iter__(self):
        """Iterator over the parameter name strings in the label of this VicarImage.
        It returns a name string if that name is unique, otherwise a tuple (name,
        occurrence)."""

        return self._label.__iter__()

    def names(self, pattern=None):
        """Iterator for the VICAR parameter name strings in the label of this VicarImage.

        Implemented as a simple list.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
        """

        return self._label.names(pattern=pattern)

    def keys(self, pattern=None):
        """Iterator over the keys in the label of this VicarImage. The key is the
        parameter name if it is unique or (name, occurrence number) otherwise.

        Implemented as a simple list.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
        """

        return self._label.keys(pattern=pattern)

    def values(self, pattern=None):
        """Iterator over the values in the label of this VicarImage.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
        """

        return self._label.values(pattern=pattern)

    def items(self, pattern=None, unique=True):
        """Iterator over the (key, value) pairs in the label of this VicarImage.

        Input:
            pattern     optional regular expression. If provided, the iteration only
                        includes parameter names that match the pattern.
            unique      True to return unique keys, in which non-unique names are replaced
                        by tuples (name, occurrence). If False, all keys are name strings,
                        and a string may appear multiple times.
        """

        return self._label.items(pattern=pattern, unique=unique)

    def args(self, pattern=None):
        """Iterator over the numerical indices of the keywords."""

        return self._label.args(pattern=pattern)

    def as_dict(self):
        """The VicarLabel object, provided primarily for backward compatibility."""

        return self._label

##########################################################################################
