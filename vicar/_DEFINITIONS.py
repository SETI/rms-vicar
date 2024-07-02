##########################################################################################
# vicar/_DEFINITIONS.py
##########################################################################################
"""Definitions of global variables defining attributes of the VICAR standard.

Source: https://github.com/SETI/rms-vicar/blob/main/vicar/_DEFINITIONS.py
"""

import sys

# Fixed space between "LBLSIZE=" and the next parameter name
_LBLSIZE_WIDTH = 16

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

# Infer the _HOST dictionary key for this platform
try:
    _HOST = _HOST_DICT[(sys.byteorder, sys.platform)]
except KeyError:                # pragma: no cover
    if sys.platform.startswith('linux'):
        _HOST = 'X86-LINUX'     # could be "linux4" I guess
    else:
        _HOST = sys.platform.upper()

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

# Keywords that the user cannot modify
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

# Keywords with enumerated values
_ENUMERATED_VALUES = {
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

# Keywords that must be positive ints
_REQUIRED_INTS = {'LBLSIZE', 'RECSIZE', 'NL', 'NS', 'NB', 'N1', 'N2', 'N3', 'NBB', 'NLB'}

##########################################################################################
