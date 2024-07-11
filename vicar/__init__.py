##########################################################################################
# vicar/__init__.py
##########################################################################################
"""
VICAR File Support Module,
PDS Ring-Moon Systems Node, SETI Institute

**Introduction**

`vicar` is a Python module that supports reading and writing of JPL’s VICAR file format.
It supports the definition of the VICAR file format as found here:

    https://pds-rings.seti.org/help/VICAR_file_fmt.pdf

**Getting Started**

The `vicar` modules provies these classes:

    * `VicarLabel`: Class for reading, writing, and parsing of VICAR labels.
    * `VicarImage`: Class for handling VICAR image (and other) data files.
    * `VicarError`: Extension of class ValueError to contain exceptions.

To read a VICAR image file::

    import vicar
    vic = vicar.VicarImage("path/to/file")

The returned `VicarImage` object "vic" has these attributes:

    * `vic.array`: The 3-D data array converted to native format.
    * `vic.array2d`: Same as above, but with leading dimension (typically, bands)
      stripped.
    * `vic.prefix`: The array prefix bytes as a 3-D array of unsigned bytes.
    * `vic.prefix2d`: Same as above, but with the leading dimension stripped.
    * `vic.binheader`: The binary header as a bytes object; use vic.binheader_array() to
      extract information.
    * `vic.label`: The internal VicarLabel object that manages the VICAR label
      information, if direct access is needed.

VICAR parameter values can be extracted from the label using dictionary-like syntax::

    len(vic)                # the number of parameters in the VICAR label.
    vic['LBLSIZE']          # the value of the LBLSIZE parameter (an integer).
    vic[0]                  # the value of the first parameter.
    vic[-1]                 # the value of the last parameter.
    vic['LBLSIZE',-1]       # the value of the last occurrence of the LBLSIZE parameter.
    vic.get(('LBLSIZE',2), 99)
                            # the value of the third occurrence of the LBLSIZE
                            # parameter, or 99 if there are fewer than 3 occurrences.
    vic.arg('LBLSIZE')      # the numeric index of "LBLSIZE" among the VICAR parameters.

You can also use dictionary-like syntax to modify and insert header values::

    vic['SOLDIST'] = 1.e9   # set SOLDICT to this value.
    del vic['SOLDIST',0]    # Remove the first occurrence of SOLDIST from the label.
    vic['LBLSIZE+'] = 2000  # insert a new LBLSIZE parameter instead of modifying an
                            # existing one.

Note that certain required VICAR parameters contain structural information about the
file; these cannot generally be modified directly.

Numerous methods are available to iterate over the VICAR label parameters::

    for (name,value) in vic.items(): ...
    for key in vic.keys(): ...
    for name in vic.names(): ...
    for value in vic.values(): ...

Iterators can take a regular expression as input to restrict the items returned::

    for value in vic.values(r'LAB\\d\\d'): ...

Use `str(vic)` to get the VICAR label content represented as a string.

Here are the steps to create and write a VICAR image file::

    vic = VicarImage()
    vic.array = array
    vic.prefix = prefix
    vic.binheader = binheader
    vic['NOTES'] = ['add as many more VICAR parameters', 'as you wish']
    vic.write_file("path/to/file")
"""

__all__ = ['VicarError', 'VicarImage', 'VicarLabel']

from vicar.vicarlabel import VicarLabel, VicarError
from vicar.vicarimage import VicarImage

try:
    from ._version import __version__
except ImportError:
    __version__ = 'Version unspecified'

##########################################################################################
