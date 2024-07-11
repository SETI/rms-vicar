##########################################################################################
# vicar/vicarimage.py
##########################################################################################
"""Class to support accessing, reading, and modifying VICAR image files."""

import numpy as np
import pathlib
import sys
import vax
import warnings

try:
    from _version import __version__
except ImportError:
    __version__ = 'Version unspecified'

from vicar.vicarlabel import VicarLabel, VicarError
from vicar._DEFINITIONS import _DTYPE_FROM_FORMAT, _FORMAT_FROM_DTYPE, _HOST, _IMMUTABLE


class VicarImage():
    """Constructor for a VicarImage.

    This class defines the contents of a VICAR data file. It supports methods for reading
    and writing files and for accessing header information.

    **Properties**:

        * `array`: The 3-D data array converted to native format.
        * `array3d`: Same as above.
        * `array2d`: Same as above, but with leading dimension (typically, bands)
          stripped.
        * `prefix`: The array prefix bytes as a 3-D array of unsigned bytes.
        * `prefix3d`: Same as above.
        * `prefix2d`: Same as above, but with the leading dimension stripped.
        * `binheader`: The binary header as a bytes object; use vic.binheader_array() to
          extract information.
        * `label`: The internal object that manages the VICAR label information, available
          if direct access to it is needed.

    **Core Methods:**

        * `arg`: The index of a parameter name within this label.
        * `args`: Iterator over the numeric indices of the parameters in a label.
        * `binheader_array`: Interpret the content of a binary header.
        * `copy`: A copy of this VicarImage.
        * `deepcopy`: An independent (deep) copy of this VicarImage.
        * `from_array`: Construct a VicarImage object for a NumPy array.
        * `from_file`: Construct a VicarImage object from the content of a VICAR data
          file.
        * `get`: Retrieve a label parameter value or return a default.
        * `items`: Iterator over the (name, value) tuples in the label.
        * `keys`: Iterator over the parameter names in the label as unique keys.
        * `names`: Iterator over the parameter names in the label.
        * `values`: Iterator over the parameter values in the label.
        * `write_file`: Write this object as a VICAR data file.

    **Python Syntax Support Methods:**

        * `__contains__`: Enables "`name in image`" syntax for checking a name in the
          label.
        * `__delitem__`: Enables "`del image[name]`" syntax to remove a label parameter
          name.
        * `__eq__`: Enables "`a == b`', the test of whether two image objects are equal.
        * `__getitem__`: Enables "`image[name]`" dictionary-like syntax to get the value
          of a label parameter.
        * `__iter__`: Enables "`for key in image:`" syntax to iterate over the label
          parameter keys.
        * `__len__`: Enables "`len(image)`", the number of parameters in the image's
          label.
        * `__repr__`: Enables "`repr(image)`", similar to the "`str(label)`", but with the
          class name included.
        * `__setitem__`: Enables "`image[name] = value`" dictionary-like syntax to set the
          value of a label parameter.
        * `__str__`: Enables "`str(image)`", returning a string representing the content
          of a label.

    **Notes About Dictionary Keys:**

        When using dictionary-like syntax to reference a parameter in a VICAR label, a
        rich set of options are available. For example, if `image` is a VicarImage object,
        then:

            * `image[n]` where `n` is an integer refers to the "nth" parameter in the
              label. `n` can be positive or negative.
            * `image[name]` where `name` is a string refers to the first occurrence in
              the label of a parameter with this name.
            * `image[name,n]` refers to the "nth" occurrence in the label of a parameter
              with this name. `n` can be positive or negative.
            * `image[name, after]` where both items are strings refers to the first
              occurrence of parameter `name` after the first occurrence of parameter
              `after` and before the second occurrence of `after`.
            * `image[name, after, value]` refers to the first occurrence of parameter
              `name` after the first location where `after` equals `value` and before the
              next occurrence of `after`.

        The last two options make it easy to reference a VICAR label parameter that is
        repeated. For example, "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies
        the occurrence of `DAT_TIM` applicable to `TASK='COPY'` when there might be other
        `TASK` sections of the image label containing other values of `DAT_TIM`.

        Append a "+" to `name` to expand upon the function's behavior. With "get"
        operations, a list is returned identifying all of the occurrences of the selected
        name rather than just the first or "nth". With "set" operations, a new occurrence
        of `name` is inserted into the label even if the a parameter of the given name is
        already present.
    """

    def __init__(self, source=None, array=None, *, prefix=None, binheader=None,
                 strict=True):
        """Constructor for a VicarImage object.

        Parameters:
            source (pathlib.Path, str, or VicarLabel, optional):
                Source for the VicarImage based on a file path or VicarLabel; if not
                specified (equvalent to source=None), a minimal label is created.
            array (array-like, optional):
                Optional data array for this object. If the source is a file path,
                this array will override that in the file.
            prefix (array-like, optional):
                Optional prefix bytes for this object. If the source is a file
                path, this value will override that in the file. To remove the
                prefix array found in the file, use prefix=[].
            binheader (array-like or bytes, optional):
                Optional binary header for this data file. If the source is a
                file path, this value will override that in the file. To remove
                the binheader found in the file, use binheader=b''.
            strict (bool, optional):
                True (the default) to require strict conformance to the VICAR standard;
                False for a looser version of the standard. If `source` is a VicarLabel,
                this input is ignored; the value already assigned to the `source` is used
                instead.
        """

        self._filepath = None

        if not source:
            self._label = VicarLabel([], strict=strict)
        elif isinstance(source, VicarLabel):
            self._label = source
        else:
            self._filepath = pathlib.Path(source)
            info = VicarImage._read_file(self.filepath, extraneous='ignore',
                                         strict=strict)
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

    ######################################################################################
    # Properties
    ######################################################################################

    @property
    def filepath(self):
        """The path to the associated file.

        Returns:
            pathlib.Path or None: The path to the associated file, if any.
        """

        return self._filepath

    @filepath.setter
    def filepath(self, value):
        """Set the path to the associated file.

        Parameters:
            value (pathlib.Path, str, or None):
                The path to the associated file; None to remove a file association.
        """

        if value is None:
            self._filepath = None
        else:
            self._filepath = pathlib.Path(value)

    @property
    def label(self):
        """The VicarLabel object.

        Returns:
            VicarLabel: The VicarLabel object.
        """

        return self._label

    @property
    def array2d(self):
        """The data array as 2-D.

        Returns:
            np.ndarray or None:
                The data array as 2-dimensional if it is present; otherwise, None.

        Raises:
            VicarError: If the array has more than two dimensions.
        """

        if self._array is None:
            return None
        if self._array.shape[0] != 1:
            raise VicarError(f'VICAR array shape {self._array.shape} is not 2-D')
        return self._array[0]

    @property
    def data_2d(self):
        """The data array as 2-D; DEPRECATED name.

        Returns:
            np.ndarray or None:
                The data array as 2-dimensional if it is present; otherwise, None.

        Raises:
            VicarError: If the array has more than two dimensions.
        """

        return self.array2d

    @property
    def array3d(self):
        """The data array as 3-D.

        Returns:
            np.ndarray or None:
                The data array as 3-dimensional if it is present; otherwise, None.
        """

        return self._array

    @property
    def data_3d(self):
        """The data array as 3-D; DEPRECATED name.

        Returns:
            np.ndarray or None:
                The data array as 3-dimensional if it is present; otherwise, None.
        """

        return self._array

    @property
    def array(self):
        """The data array.

        Returns:
            np.ndarray or None: The data array if it is present; otherwise, None.
        """

        return self._array

    @array.setter
    def array(self, value):
        """Set the data array.

        Parameters:
            value (array-like or None):
                The prefix array or None to remove the data array.

        Raises:
            VicarError:
                If the array shape is incompatible with an existing prefix or binary
                header.
        """

        if value is None:
            self._array = None
            return

        value = np.asarray(value)
        if value.ndim != 3:
            value = value.reshape((3-value.ndim) * (1,) + value.shape)  # reshape to 3-D
        VicarImage._check_array_vs_prefix(value, self._prefix)

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
        (self._label['FORMAT'], isint) = VicarImage._format_isint(value)
        if isint:
            if value.itemsize > 1:
                self._label['INTFMT'] = VicarImage._intfmt(value)
        else:
            self._label['REALFMT'] = VicarImage._realfmt(value)

        self._label['RECSIZE'] = recsize
        self._label['NLB'] = nlb
        self._label._set_n321(*value.shape)

    @property
    def prefix2d(self):
        """The image prefix as a 2-D array.

        Returns:
            np.ndarray: The image prefix as a 2-dimensional array.

        Raises:
            VicarError: If the prefix array has more than two dimensions.
        """

        if self._prefix is None:
            return None
        if self._prefix.shape[0] != 1:
            raise VicarError(f'prefix bytes shape {self._prefix.shape} is not 2-D')
        return self._prefix[0]

    @property
    def prefix_2d(self):
        """The image prefix as a 2-D array; DEPRECATED name.

        Returns:
            np.ndarray: The image prefix as a 2-dimensional array.

        Raises:
            VicarError: If the prefix array has more than two dimensions.
        """

        return self.prefix2d

    @property
    def prefix3d(self):
        """The image prefix as a 3-D array.

        Returns:
            np.ndarray: The image prefix as a 3-dimensional array.
        """

        return self._prefix

    @property
    def prefix_3d(self):
        """The image prefix as a 3-D array; DEPRECATED name.

        Returns:
            np.ndarray: The image prefix as a 2-dimensional array.
        """

        return self._prefix

    @property
    def prefix(self):
        """The image prefix object.

        Returns:
            np.ndarray: The image prefix as a 2-dimensional array.
        """

        return self._prefix

    @prefix.setter
    def prefix(self, value):
        """Set the image prefix array.

        Parameters:
            value (array-like or None):
                The prefix array or None to remove the prefix array.

        Raises:
            VicarError:
                If the array shape is incompatible with an existing data array or binary
                header.
        """

        if value is None:
            nbb = 0
        else:
            value = np.asarray(value)
            if value.size == 0:
                nbb = 0
                value = None
            else:
                if value.ndim != 3:
                    value = value.reshape((3-value.ndim) * (1,) + value.shape)
                VicarImage._check_array_vs_prefix(self._array, value)
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
            (fmt, isint) = VicarImage._format_isint(value)

            # Prefix defines attributes left undefined by array
            if self._array is None:
                self._label['FORMAT'] = fmt

            if isint:
                if self._array is None or self._array.dtype.kind in 'fc':
                    if value.itemsize > 1:
                        self._label['INTFMT'] = VicarImage._intfmt(value)
            else:
                if self._array is None or self._array.dtype.kind in 'ui':
                    self._label['REALFMT'] = VicarImage._realfmt(value)

    @property
    def binheader(self):
        """The binary header as an array or bytes object.

        Returns:
            np.ndarray, bytes, or None: The binary header if present; otherwise, None.
        """

        return self._binheader

    @binheader.setter
    def binheader(self, value):
        """Set the binary header.

        Parameters:
            value (bytes, np.ndarray, or None):
                The binary header or None to remove the binary header.

        Raises:
            VicarError:
                If the header length is incompatible with the existing RECSIZE.
        """

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
                self._label['BREALFMT'] = VicarImage._realfmt(value)
            elif value.dtype.kind in 'ui' and value.dtype.itemsize > 1:
                self._label['BINTFMT'] = VicarImage._intfmt(value)

    ######################################################################################
    # Support for the Standard Python API
    ######################################################################################

    def copy(self):
        """A copy of this VicarImage.

        The copied label is independent of the original, but the data and prefix array
        are shared.

        Returns:
            VicarImage: The copy.
        """

        return VicarImage(source=self.label.copy(), array=self._array,
                          prefix=self._prefix, binheader=self._binheader)

    def deepcopy(self):
        """An independent (deep) copy of this VicarImage.

        Returns:
            VicarImage: The deep copy.
        """

        vim = self.copy()
        vim._array = None if self._array is None else self._array.copy()
        vim._prefix = None if self._prefix is None else self._prefix.copy()
        return vim

    def __eq__(self, other):
        """True if this VicarImage is equal to the given object.

        VicarImages are equal if the label content, data array, prefix array, binary
        header are all equal. Label formatting hints need not be the same.

        Parameters:
            other (VicarImage): Second VicarImage to compare with this.

        Returns:
            bool: True if the objects are equal.
        """

        if not isinstance(other, VicarImage):
            return False

        prefix1 = b'' if self._prefix is None else bytes(self._prefix)
        prefix2 = b'' if other._prefix is None else bytes(other._prefix)

        binheader1 = b'' if self._binheader is None else bytes(self._binheader)
        binheader2 = b'' if other._binheader is None else bytes(other._binheader)

        return (self._label == other._label
                and np.all(self._array == other._array)
                and prefix1 == prefix2
                and binheader1 == binheader2)

    def __str__(self):
        return str(self._label)

    def __repr__(self):
        return 'VicarImage("""' + self._label.as_string(sep='\n\n') + '""")'

    ######################################################################################
    # Public API
    ######################################################################################

    @staticmethod
    def from_file(filepath, extraneous='ignore', strict=True):
        """VicarImage object from an existing VICAR image file.

        Parameters:
            filepath (pathlib.Path or str): Path to an existing VICAR data file.

            extraneous (str, optional):
                How to handle the presence of extraneous bytes at the end of the file, one
                of:

                * "error"   to raise VicarError;
                * "warn"    to raise a UserWarning;
                * "print"   to print a message;
                * "ignore"  to ignore;
                * "include" to include the extraneous bytes as part of the return.

            strict (bool, optional):
                True (the default) to require strict conformance to the VICAR standard;
                False for a looser version of the standard.

        Returns:
            VicarImage or (VicarImage, bytes or None): A VicarImage or a tuple containing:

            * VicarImage: A new object containing the content of the specified file.
            * bytes or None: Any extraneous bytes from the end of the file, included if
              `extraneous` equals "include".
        """

        info = VicarImage._read_file(filepath, extraneous=extraneous, strict=strict)
        (label, data, prefix, binheader) = info[:4]
        vim = VicarImage(source=label, array=data, prefix=prefix, binheader=binheader)

        if extraneous == 'include':
            return (vim, info[4])

        return vim

    @staticmethod
    def from_array(array, strict=True):
        """Construct a VicarImage object for an array.

        Parameters:
            array (array-like): The data array to use in this VicarImage object.
            strict (bool, optional):
                True (the default) to require strict conformance to the VICAR standard;
                False for a looser version of the standard.

        Returns:
            VicarImage: A new VicarImage object containing this data array.
        """

        return VicarImage(source=[], array=array, strict=strict)

    def write_file(self, filepath=None):
        """Write the VicarImage object into a file.

        Parameters:
            filepath (path.Pathlib or str, optional):
                Optional the path of the file to write. If not specified but this object's
                filepath attribute is defined, it will write to this file.
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

    def binheader_array(self, kind='', size=None):
        """The numbers embedded in a binary header.

        This method is capable of reading "ISIS" table files when those tables consist
        entirely of a single data format. It uses the FMT_DEFAULT parameter to determine
        dtype, and uses the NR and NC values, if present, to determine the number of rows
        and columns in the table.

        Parameters:
            kind (str, optional):
                Optional single-letter code for the data type: "u" for unsigned int; "i"
                for signed int; "f" for float. If not specified, the kind is inferred from
                the value of the FMT_DEFAULT parameter.
            size (int, optional):
                Number of bytes per value. If not provided, it is inferred from the
                FMT_DEFAULT parameter if present. Otherwise, the default is 1 for kind =
                "u"; 2 for kind = "i"; 4 for kind = "f".

        Returns:
            np.ndarray or None:
                The binary header as an array; None if there is no binary header.
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
            dtype = dpref + kind + str(size)

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

    ######################################################################################
    # File I/O
    ######################################################################################

    @staticmethod
    def _read_file(filepath, *, extraneous='ignore', strict=True):
        """The VICAR data array, binary header, and prefix bytes from the specified
        data file.

        Parameters:
            filepath (pathlib.Path or str): Path to an existing VICAR data file.

            extraneous (str, optional):
                How to handle the presence of extraneous bytes at the end of the file, one
                of:

                * "error"   to raise VicarError;
                * "warn"    to raise a UserWarning;
                * "print"   to print a message;
                * "ignore"  to ignore;
                * "include" to include the extraneous bytes as part of the return.

            strict (bool, optional): True (the default) to require strict conformance to
                the VICAR standard; False for a looser version of the standard.

        Returns:
            (VicarLabel, np.ndarray, np.ndarray or None, bytes[, bytes]):
            A tuple containing:

            * VicarLabel: The label.
            * np.ndarray: The data as a 3D array converted to native format.
            * np.ndarray or None: The prefix array as a 3D array of unsigned bytes if
              present; otherwise, None.
            * bytes: The binary header if present; otherwise, None.
            * bytes, optional: Any extraneous bytes at the end of the file, included if
              `extraneous` equals "include".

        Raises:
            OSError: If the referenced file could not be read.
            ValueError: If `extraneous` does not have a valid value.
            VicarError: If the referenced file does not conform to the VICAR standard.
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
            ldict = VicarLabel(label, strict=strict)
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

    ######################################################################################
    # Public methods inherited from the VicarLabel object
    ######################################################################################

    def __len__(self):
        """The number of keywords in the label of this VicarImage.

        Returns:
            int: Number of parameters in the VICAR label
        """

        return len(self._label)

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
                that is repeated. For example, if `image` is a VicarImage, then
                "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies the occurrence of
                `DAT_TIM` applicable to `TASK='COPY'` when there might be other `TASK`
                sections of the label containing other values of `DAT_TIM`.

                Append a "+" to the name to return a list of all values where the
                constraints are satisfied, starting with the first or "nth".

        Returns:
            int, float, string, or list:
                The value of the indexed parameter if there is no name ending in "+";
                otherwise, a list of all the parameter values starting with the "nth".

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

        return self._label.__getitem__(key)

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
                that is repeated. For example, if `image` is a VicarImage, then
                "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies the occurrence of
                `DAT_TIM` applicable to `TASK='COPY'` when there might be other `TASK`
                sections of the label containing other values of `DAT_TIM`.

                Append a "+" to the name to return a list of all values where the
                constraints are satisfied, starting with the first or "nth".

            default (int, float, str, or list): The value to return if the key is not
                found.

        Returns:
            int, float, str, or list:
                If a name is provided that ends in a plus, the returned value will be the
                list of all values of the selected key, or else `[default]` if the list
                would be empty or the key would raise an error.

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

        return self._label.get(key, default)

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
                that is repeated. For example, if `image` is a VicarImage, then
                "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies the occurrence of
                `DAT_TIM` applicable to `TASK='COPY'` when there might be other `TASK`
                sections of the label containing other values of `DAT_TIM`.

                Append a "+" to the name to force a new occurrence of the key to be
                inserted, even if the key already exists.

            value (int, float, string, list, or tuple): Value to assign to the indexed
                entry in the label.

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

        name = self._label._get_name(key)
        has_plus = VicarLabel._has_plus(key)
        if not has_plus and name in _IMMUTABLE:
            indx = self._label.arg(key)
            if indx == self._label._key_index[name][0]:      # if first occurrence
                raise VicarError(f'VICAR parameter {name} cannot be modified')

        self._label.__setitem__(key, value)

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
                that is repeated. For example, if `image` is a VicarImage, then
                "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies the occurrence of
                `DAT_TIM` applicable to `TASK='COPY'` when there might be other `TASK`
                sections of the label containing other values of `DAT_TIM`.

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

        name = self._label._get_name(key)
        if name in _IMMUTABLE:
            indx = self._label.arg(VicarLabel._remove_plus(key))
            if indx == self.label._key_index[name][0]:      # if first occurrence
                raise VicarError(f'VICAR parameter {name} cannot be deleted')

        self._label.__delitem__(key)

    def __contains__(self, key):
        """True if the given key can is found in the label of this VicarImage.

        Parameters:
            key (int, str, or tuple): The key identifying the label parameter to check.

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
                that is repeated. For example, if `image` is a VicarImage, then
                "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies the occurrence of
                `DAT_TIM` applicable to `TASK='COPY'` when there might be other `TASK`
                sections of the label containing other values of `DAT_TIM`.

        Returns:
            bool: True if the key is found within the label.
        """

        return self._label.__contains__(key)

    def arg(self, key):
        """The index or indices of the keyed item in the label of this VicarImage.

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
                that is repeated. For example, if `image` is a VicarImage, then
                "`image['DAT_TIM', 'TASK', 'COPY']`" uniquely identifies the occurrence of
                `DAT_TIM` applicable to `TASK='COPY'` when there might be other `TASK`
                sections of the label containing other values of `DAT_TIM`.

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
                If "+" is appended to `name`, the list of all positive indices that
                identify matching parameters, starting with the "nth". Otherwise, the
                single positive index into the label identifying the parameter.

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

        return self._label.arg(key)

    def __iter__(self):
        """Iterator over the unique names or (name, occurrence) pairs in the label of
        this VicarImage.

        Returns:
            iterator:
                The parameter keys within this label, in order. The key is the parameter
                name if it is unique or (name, occurrence number) otherwise.
        """

        return self._label.__iter__()

    def names(self, pattern=None):
        """Iterator for the VICAR parameter name strings in the label of this VicarImage.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            list: The matching parameter names within this label, in order.
        """

        return self._label.names(pattern=pattern)

    def keys(self, pattern=None):
        """Iterator over the keys in the label of this VicarImage. The key is the
        parameter name if it is unique or (name, occurrence number) otherwise.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            list:
                The parameter keys within this label, in order. Each key is the parameter
                name if it is unique or (name, occurrence number) otherwise.
        """

        return self._label.keys(pattern=pattern)

    def values(self, pattern=None):
        """Iterator over the values in the label of this VicarImage.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            iterator: The values of the matching parameters within this label, in order.
        """

        return self._label.values(pattern=pattern)

    def items(self, pattern=None, unique=True):
        """Iterator over the (key, value) pairs in the label of this VicarImage.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.
            unique (bool, optional):
                True to return unique keys, in which non-unique names are replaced by
                tuples (name, occurrence). If False, all keys are name strings, and a name
                may appear multiple times.

        Returns:
            iterator:
                Tuples (name, value) of the matching parameter names within this label, in
                order.
        """

        return self._label.items(pattern=pattern, unique=unique)

    def args(self, pattern=None):
        """Iterator over the numerical indices of the keywords in the label of this
        VicarImage.

        Parameters:
            pattern (str or re.Pattern, optional):
                Regular expression that can be used to filter the label parameter names.

        Returns:
            iterator:
                The indices of the matching parameter names within this label, in order.
        """

        return self._label.args(pattern=pattern)

    def as_dict(self):
        """The VicarLabel object.

        DEPRECATED, provided primarily for backward compatibility. Use the `label`
        property instead, because it behaves as a dictionary.

        Returns:
            VicarLabel: The VicarLabel object associated with this VicarImage.
        """

        return self._label

    ######################################################################################
    # Utilities
    ######################################################################################

    def _intfmt(x):
        """Determine the INTFMT based on the dtype of an array."""

        if isinstance(x, np.ndarray):
            if x.dtype.byteorder == '<':    # pragma: no cover
                return 'LOW'
            if x.dtype.byteorder == '>':    # pragma: no cover
                return 'HIGH'

        return 'LOW' if sys.byteorder == 'little' else 'HIGH'

    def _realfmt(x):
        """Determine the REALFMT value based on the dtype of an array."""

        if isinstance(x, np.ndarray):
            if x.dtype.byteorder == '>':    # pragma: no cover
                return 'IEEE'
            if x.dtype.byteorder == '<':    # pragma: no cover
                return 'RIEEE'

        return 'RIEEE' if sys.byteorder == 'little' else 'IEEE'

    def _format_isint(x):
        """True if this array contains integer values."""

        try:
            key = x.dtype.kind + str(x.itemsize)
            return _FORMAT_FROM_DTYPE[key]
        except KeyError:
            raise VicarError(f'array dtype "{x.dtype}" is not supported by VICAR')

    def _check_array_vs_prefix(array, prefix):
        """Raise an exception if the given image array and prefix byte array are not
        compatible.

        Parameters:
            array (np.ndarray or None): A data array.
            prefix (np.ndarray or None): A prefix array.

        Raises:
            VicarError: If the arrays are invalid or inconsistent with one another.
        """

        if array is not None and array.ndim != 3:
            raise VicarError(f'data array shape {array.shape} is not 2-D or 3-D')

        if prefix is not None and prefix.ndim != 3:
            raise VicarError(f'prefix array shape {prefix.shape} is not 2-D or 3-D')

        if array is None or prefix is None:
            return

        if array.shape[:-1] != prefix.shape[:-1]:
            raise VicarError('data and prefix arrays have incompatible shapes: '
                             f'{array.shape}, {prefix.shape}')

        (format1, isint1) = VicarImage._format_isint(array)
        if isint1:
            intfmt1 = VicarImage._intfmt(array)
        else:
            realfmt1 = VicarImage._realfmt(array)

        (format2, isint2) = VicarImage._format_isint(prefix)
        if isint2:
            intfmt2 = VicarImage._intfmt(prefix)
        else:
            realfmt2 = VicarImage._realfmt(prefix)

        if isint1 and isint2:
            if format1 != 'BYTE' and format2 != 'BYTE' and intfmt1 != intfmt2:
                raise VicarError('data and prefix array formats are incompatible: '
                                 f'{intfmt1}, {intfmt2}')
        if not isint1 and not isint2:
            if realfmt1 != realfmt2:
                raise VicarError('data and prefix array formats are incompatible: '
                                 f'{realfmt1}, {realfmt2}')

##########################################################################################
