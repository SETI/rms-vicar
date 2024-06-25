##########################################################################################
# vicar/__init__.py
##########################################################################################
"""
This module supports reading and writing of JPL's VICAR file format. It supports the
definition of the VICAR file format as found here:
https://www-mipl.jpl.nasa.gov/external/VICAR_file_fmt.pdf

The `vicar` module provides these classes:

- `VicarLabel`: Class for reading, writing, and parsing of VICAR labels.
- `VicarImage`: Class for handling VICAR image (and other) data files.
- `VicarError`: Extension of class ValueError to contain exceptions.

Details of each class are available in the module documentation:
https://rms-vicar.readthedocs.io/en/latest/module.html).
"""

__all__ = ['VicarError', 'VicarImage', 'VicarLabel']

from vicar.vicarlabel import VicarLabel, VicarError
from vicar.vicarimage import VicarImage

try:
    from ._version import __version__
except ImportError:
    __version__ = 'Version unspecified'

##########################################################################################
