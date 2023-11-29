| PyPI Release | Test Status | Code Coverage |
| ------------ | ----------- | ------------- |
| [![PyPI version](https://badge.fury.io/py/rms-vicar.svg)](https://badge.fury.io/py/rms-vicar) | [![Build status](https://img.shields.io/github/actions/workflow/status/SETI/rms-vicar/run-tests.yml?branch=master)](https://github.com/SETI/rms-vicar/actions) | [![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-vicar/main?logo=codecov)](https://codecov.io/gh/SETI/rms-vicar) |

# rms-vicar

PDS Ring-Moon Systems Node, SETI Institute

Supported versions: Python >= 3.7

Classes and methods to read and write JPL's VICAR-format data files:

    VicarLabel      class for reading, writing, and parsing of VICAR labels.
    VicarImage      class for handling VICAR image (and other) data files.
    VicarError      extension of class ValueError to contain exceptions.

This module supports the definition of the VICAR file format as found here:

[https://www-mipl.jpl.nasa.gov/external/VICAR_file_fmt.pdf](https://www-mipl.jpl.nasa.gov/external/VICAR_file_fmt.pdf)

To read a VICAR image file:

    vic = VicarImage("path/to/file")
    vic.array     = the 3-D data array converted to native format.
    vic.array2d   = same as above, but with leading dimension (typically, bands) stripped.
    vic.prefix    = the array prefix bytes as a 3-D array of unsigned bytes.
    vic.prefix2d  = same as above, but with the leading dimension stripped.
    vic.binheader = the binary header as a bytes object; use vic.binheader_array() to
                  = extract information.
    vic.label     = the internal VicarLabel object that manages the VICAR label
                    information, if direct access is needed.

VICAR parameter values can be extracted from the label using dictionary-like syntax:

    len(vic)          = the number of parameters in the VICAR label.
    vic['LBLSIZE']    = the value of the LBLSIZE parameter (an integer).
    vic[0]            = the value of the first parameter.
    vic[-1]           = the value of the last parameter.
    vic['LBLSIZE',-1] = the value of the last occurrence of the LBLSIZE parameter.
    vic.get(('LBLSIZE',2), 99) = the value of the third occurrence of the LBLSIZE
                        parameter, or 99 if there are fewer than 3 occurrences.
    vic.arg('LBLSIZE') = the numeric index of "LBLSIZE" among the VICAR parameters.

You can also use dictionary-like syntax to modify and insert header values:

    vic['SOLDIST'] = 1.e9   # set SOLDICT to this value.
    del vic['SOLDIST',0]    # Remove the first occurrence of SOLDIST from the label.
    vic['LBLSIZE+'] = 2000  # insert a new LBLSIZE parameter instead of modifying an
                            # existing one.

Note that certain required VICAR parameters contain structural information about the file;
these cannot generally be modified directly.

Numerous methods are available to iterate over the VICAR label parameters:

    for (name,value) in vic.items(): ...
    for key in vic.keys(): ...
    for name in vic.names(): ...
    for value in vic.values(): ...

Iterators can take a regular expression as input to restrict the items returned:

    for value in vic.values(r'LAB\d\d'): ...

Use `str(vic)` to get the VICAR label content represented as a string.

Here are the steps to create and write a VICAR image file:

    vic = VicarImage()
    vic.array = array
    vic.prefix = prefix
    vic.binheader = binheader
    vic['NOTES'] = ['add as many more VICAR parameters', 'as you wish']
    vic.write_file("path/to/file")
