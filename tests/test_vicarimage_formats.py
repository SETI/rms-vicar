##########################################################################################
# tests/test_vicarimage_formats.py
# VicarImage helpers that derive INTFMT, REALFMT, and FORMAT from NumPy dtypes
##########################################################################################

import sys

import numpy as np
import pytest

from vicar.vicarimage import VicarImage
from vicar.vicarlabel import VicarError


_SYS_INTFMT = 'LOW' if sys.byteorder == 'little' else 'HIGH'
_SYS_REALFMT = 'RIEEE' if sys.byteorder == 'little' else 'IEEE'


@pytest.mark.parametrize(('array', 'expected'), [
    (np.arange(10, dtype='<i8'), 'LOW'),
    (np.arange(10, dtype='>i8'), 'HIGH'),
    (np.arange(10, dtype='<f8'), 'LOW'),
    (np.arange(10, dtype='>f8'), 'HIGH'),
    (np.arange(10), _SYS_INTFMT),
    (np.arange(10, dtype='uint8'), _SYS_INTFMT),
])
def test_vicarimage_intfmt(array: np.ndarray, expected: str) -> None:
    """INTFMT follows the byte order of the dtype, or the host if it has none."""

    assert VicarImage._intfmt(array) == expected


@pytest.mark.parametrize(('array', 'expected'), [
    (np.arange(10, dtype='<i8'), 'RIEEE'),
    (np.arange(10, dtype='>i8'), 'IEEE'),
    (np.arange(10, dtype='<f8'), 'RIEEE'),
    (np.arange(10, dtype='>f8'), 'IEEE'),
    (np.arange(10.), _SYS_REALFMT),
    (np.arange(10, dtype='uint8'), _SYS_REALFMT),
])
def test_vicarimage_realfmt(array: np.ndarray, expected: str) -> None:
    """REALFMT follows the byte order of the dtype, or the host if it has none."""

    assert VicarImage._realfmt(array) == expected


@pytest.mark.parametrize(('dtype', 'expected'), [
    ('uint8', ('BYTE', True)),
    ('<f4', ('REAL', False)),
    ('>f4', ('REAL', False)),
])
def test_vicarimage_format_isint(dtype: str, expected: tuple[str, bool]) -> None:
    """The VICAR FORMAT and whether it is an integer type come from the dtype."""

    assert VicarImage._format_isint(np.arange(10, dtype=dtype)) == expected


def test_vicarimage_format_isint_unsupported() -> None:
    """A dtype VICAR cannot represent raises VicarError."""

    with pytest.raises(VicarError):
        VicarImage._format_isint(np.arange(10., dtype='c16'))


@pytest.mark.parametrize(('array', 'prefix'), [
    (None, None),
    (np.zeros((1, 100, 200)), None),
    (np.zeros((100, 200, 300)), None),
    (None, np.zeros((100, 200, 300))),
    (np.zeros((1, 100, 200)), np.zeros((1, 100, 20))),
    (np.zeros((100, 200, 30)), np.zeros((100, 200, 30))),
    (np.zeros((1, 200, 100), dtype='uint8'), np.zeros((1, 200, 20), dtype='<i4')),
    (np.zeros((1, 200, 100), dtype='<i4'), np.zeros((1, 200, 20), dtype='uint8')),
    (np.zeros((1, 200, 100), dtype='<f4'), np.zeros((1, 200, 20), dtype='uint8')),
    (np.zeros((1, 200, 100), dtype='<f4'), np.zeros((1, 200, 20), dtype='>i2')),
    (np.zeros((1, 200, 100), dtype='<f8'), np.zeros((1, 200, 20), dtype='<f4')),
    (np.zeros((1, 200, 100), dtype='<i4'), np.zeros((1, 200, 20), dtype='<i2')),
])
def test_vicarimage_check_array_vs_prefix(array: np.ndarray | None,
                                          prefix: np.ndarray | None) -> None:
    """Arrays of matching shape and compatible byte order are accepted."""

    VicarImage._check_array_vs_prefix(array, prefix)


@pytest.mark.parametrize(('array', 'prefix'), [
    (np.arange(10), None),
    (None, np.arange(10)),
    (np.zeros((10, 10)), None),
    (None, np.zeros((10, 10))),
    (np.zeros((10, 10, 10, 10)), None),
    (np.zeros((1, 100, 100)), np.zeros((1, 200, 10))),
    (np.zeros((1, 200, 100), dtype='>i4'), np.zeros((1, 200, 20), dtype='<i4')),
    (np.zeros((1, 200, 100), dtype='>f4'), np.zeros((1, 200, 20), dtype='<f4')),
])
def test_vicarimage_check_array_vs_prefix_invalid(array: np.ndarray | None,
                                                  prefix: np.ndarray | None) -> None:
    """Wrong dimensions, mismatched shapes, and conflicting byte orders are rejected."""

    with pytest.raises(VicarError):
        VicarImage._check_array_vs_prefix(array, prefix)

##########################################################################################
