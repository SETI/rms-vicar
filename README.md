[![GitHub release; latest by date](https://img.shields.io/github/v/release/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/releases)
[![Test Status](https://img.shields.io/github/actions/workflow/status/SETI/rms-vicar/run-tests.yml?branch=main)](https://github.com/SETI/rms-vicar/actions)
[![Documentation Status](https://readthedocs.org/projects/rms-vicar/badge/?version=latest)](https://rms-vicar.readthedocs.io/en/latest/?badge=latest)
[![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-vicar/main?logo=codecov)](https://codecov.io/gh/SETI/rms-vicar)
<br />
[![PyPI - Version](https://img.shields.io/pypi/v/rms-vicar)](https://pypi.org/project/rms-vicar)
[![PyPI - Format](https://img.shields.io/pypi/format/rms-vicar)](https://pypi.org/project/rms-vicar)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rms-vicar)](https://pypi.org/project/rms-vicar)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rms-vicar)](https://pypi.org/project/rms-vicar)
<br />
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/SETI/rms-vicar/latest)](https://github.com/SETI/rms-vicar/commits/main/)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/commits/main/)
[![GitHub last commit](https://img.shields.io/github/last-commit/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/commits/main/)
<br />
[![Number of GitHub open issues](https://img.shields.io/github/issues-raw/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/issues)
[![Number of GitHub closed issues](https://img.shields.io/github/issues-closed-raw/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/issues)
[![Number of GitHub open pull requests](https://img.shields.io/github/issues-pr-raw/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/pulls)
[![Number of GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/pulls)
<br />
![GitHub License](https://img.shields.io/github/license/SETI/rms-vicar)
[![Number of GitHub stars](https://img.shields.io/github/stars/SETI/rms-vicar)](https://github.com/SETI/rms-vicar/stargazers)
![GitHub forks](https://img.shields.io/github/forks/SETI/rms-vicar)

# Introduction

`vicar` is a Python module that supports reading and writing of JPL's VICAR file format. It supports the definition of the VICAR file format as found here:
[https://pds-rings.seti.org/help/VICAR_file_fmt.pdf](https://pds-rings.seti.org/help/VICAR_file_fmt.pdf)

# Installation

The `vicar` module is available via the `rms-vicar` package on PyPI and can be
installed with:

```sh
pip install rms-vicar
```

# Getting Started

The `vicar` module provides these classes:

- [`VicarLabel`](https://rms-vicar.readthedocs.io/en/latest/module.html#vicar.VicarLabel):
  Class for reading, writing, and parsing of VICAR labels.
- [`VicarImage`](https://rms-vicar.readthedocs.io/en/latest/module.html#vicar.VicarImage):
  Class for handling VICAR image (and other) data files.
- [`VicarError`](https://rms-vicar.readthedocs.io/en/latest/module.html#vicar.VicarError):
  Extension of class ValueError to contain exceptions.

Details of each class are available in the [module documentation](https://rms-vicar.readthedocs.io/en/latest/module.html).


To read a VICAR image file:

```python
import vicar
vic = vicar.VicarImage("path/to/file")
```

The resulting object contains:

- `vic.array`: The 3-D data array converted to native format.
- `vic.array2d`: Same as above, but with leading dimension (typically, bands) stripped.
- `vic.prefix`: The array prefix bytes as a 3-D array of unsigned bytes.
- `vic.prefix2d`: Same as above, but with the leading dimension stripped.
- `vic.binheader`: The binary header as a bytes object; use `vic.binheader_array()` to
  extract information.
- `vic.label`: The internal `VicarLabel` object that manages the VICAR label information,
  if direct access is needed.

VICAR parameter values can be extracted from the label using dictionary-like syntax:

- `len(vic)`: The number of parameters in the VICAR label.
- `vic['LBLSIZE']`: The value of the LBLSIZE parameter (an integer).
- `vic[0]`: The value of the first parameter.
- `vic[-1]`: The value of the last parameter.
- `vic['LBLSIZE',-1]`: The value of the last occurrence of the LBLSIZE parameter.
- `vic.get(('LBLSIZE',2), 99)`: The value of the third occurrence of the LBLSIZE
  parameter, or 99 if there are fewer than 3 occurrences.
- `vic.arg('LBLSIZE')`: The numeric index of "LBLSIZE" among the VICAR parameters.

You can also use dictionary-like syntax to modify and insert header values:

- `vic['SOLDIST'] = 1.e9`: Set SOLDICT to this value.
- `del vic['SOLDIST',0]`: Remove the first occurrence of SOLDIST from the label.
- `vic['LBLSIZE+'] = 2000`: Insert a new LBLSIZE parameter instead of modifying an
  existing one.

Note that certain required VICAR parameters contain structural information about the file;
these cannot generally be modified directly.

Numerous methods are available to iterate over the VICAR label parameters:

```python
for (name,value) in vic.items(): ...
for key in vic.keys(): ...
for name in vic.names(): ...
for value in vic.values(): ...
```

Iterators can take a regular expression as input to restrict the items returned:

```python
for value in vic.values(r'LAB\d\d'): ...
```

Use `str(vic)` to get the VICAR label content represented as a string.

Here are the steps to create and write a VICAR image file:

```python
import vicar
vic = vicar.VicarImage()
vic.array = array
vic.prefix = prefix
vic.binheader = binheader
vic['NOTES'] = ['add as many more VICAR parameters', 'as you wish']
vic.write_file("path/to/file")
```

# Contributing

Information on contributing to this package can be found in the
[Contributing Guide](https://github.com/SETI/rms-vicar/blob/main/CONTRIBUTING.md).

# Links

- [Documentation](https://rms-vicar.readthedocs.io)
- [Repository](https://github.com/SETI/rms-vicar)
- [Issue tracker](https://github.com/SETI/rms-vicar/issues)
- [PyPi](https://pypi.org/project/rms-vicar)

# Licensing

This code is licensed under the [Apache License v2.0](https://github.com/SETI/rms-vicar/blob/main/LICENSE).
