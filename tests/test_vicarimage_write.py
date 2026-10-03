##########################################################################################
# tests/test_vicarimage_write.py
# Replacing a VicarImage's array, prefix, and binheader, and writing the result
##########################################################################################

from pathlib import Path

import numpy as np
import pytest

from vicar.vicarimage import VicarImage
from vicar.vicarlabel import VicarError


def test_vicarimage_tabular_add_image(geoma_path: Path, tmp_path: Path,
                                      rng: np.random.Generator) -> None:
    """An image and prefix added to a tabular file round-trip through write_file()."""

    test = VicarImage(geoma_path)

    with pytest.raises(VicarError):
        test.array = rng.standard_normal((100, 100))   # incompatible with binheader

    test.array = rng.standard_normal((2, 50, 72)).astype('f4')
    assert test['RECSIZE'] == 288

    with pytest.raises(VicarError):
        test.prefix = rng.integers(0, 256, (2, 50, 287), dtype='uint8')

    test.prefix = rng.integers(0, 256, (2, 50, 288), dtype='uint8')
    assert test['RECSIZE'] == 576

    dest = tmp_path / 'C2069302_GEOMA_with_image.DAT'
    test.write_file(dest)
    test2 = VicarImage.from_file(dest)
    assert test2.label == test.label
    assert np.all(test.array3d == test2.array3d)
    assert np.all(test.prefix3d == test2.prefix3d)
    assert test.binheader == test2.binheader

    # Two bands cannot be viewed as 2-D
    with pytest.raises(VicarError):
        _ = test.array2d
    with pytest.raises(VicarError):
        _ = test.prefix2d


def test_vicarimage_binheader_and_prefix(data_dir: Path, tmp_path: Path,
                                         rng: np.random.Generator) -> None:
    """binheader must fill whole records, and the prefix must fit alongside it."""

    vim = VicarImage(data_dir / 'C2069302_GEOMED.IMG')

    with pytest.raises(IndexError):
        vim[('LBLSIZE', 1)]
    assert vim.binheader is None
    assert vim.prefix is None

    wrong_size = rng.integers(0, 256, 2001, dtype='uint8')
    for binheader in (wrong_size, bytes(wrong_size), wrong_size.data):
        with pytest.raises(VicarError):
            vim.binheader = binheader

    vim.binheader = rng.integers(0, 256, 2000, dtype='uint8')

    # The prefix would change RECSIZE, so the binheader would no longer fit
    with pytest.raises(VicarError):
        vim.prefix = rng.integers(0, 32000, (1000, 2), dtype='int16')

    vim.binheader = None
    vim.prefix = rng.integers(0, 32000, (1000, 2), dtype='int16')
    vim.binheader = rng.integers(0, 256, 2004, dtype='uint8')

    dest = tmp_path / 'C2069302_GEOMED_with_prefix.IMG'
    vim.write_file(dest)
    assert vim == VicarImage(dest)

    # Removing the prefix would change RECSIZE, so the binheader would no longer fit
    with pytest.raises(VicarError):
        vim.prefix = None

    vim.binheader = None
    vim.prefix = None
    vim.write_file(dest)
    assert vim == VicarImage(dest)


def test_vicarimage_write_without_array(tmp_path: Path) -> None:
    """An image with no data cannot be written."""

    vim = VicarImage()
    with pytest.raises(VicarError):
        vim.write_file(tmp_path / 'temp.IMG')


@pytest.mark.parametrize('attr', ['prefix', 'binheader'])
@pytest.mark.parametrize(('dtype', 'name', 'expected'), [
    ('>i2', 'INTFMT', 'HIGH'),
    ('<i2', 'INTFMT', 'LOW'),
    ('>f8', 'REALFMT', 'IEEE'),
    ('<f8', 'REALFMT', 'RIEEE'),
])
def test_vicarimage_formats_from_scratch(attr: str, dtype: str, name: str, expected: str,
                                         rng: np.random.Generator) -> None:
    """With no array, a prefix or binheader sets the (B)INTFMT or (B)REALFMT."""

    vim = VicarImage()
    if attr == 'binheader':
        name = 'B' + name

    # Set the opposite byte order first, to check that it is replaced
    opposite = ('<' if dtype[0] == '>' else '>') + dtype[1:]
    for dt in (opposite, dtype):
        values = rng.integers(0, 32000, (100, 10)) if 'i' in dt else \
            rng.standard_normal((100, 10))
        setattr(vim, attr, values.astype(dt))
    assert vim[name] == expected

    assert vim['BHOST'] == vim['HOST']


def test_vicarimage_array_from_scratch(rng: np.random.Generator) -> None:
    """Assigning an array to an empty image sets the dimensions and INTFMT."""

    vim = VicarImage()
    vim.array = rng.integers(0, 32000, (200, 100)).astype('>i2')
    assert vim['INTFMT'] == 'HIGH'
    vim.array = rng.integers(0, 32000, (200, 100)).astype('<i2')
    assert vim['INTFMT'] == 'LOW'
    vim.array = rng.integers(0, 32000, (200, 100)).astype('>i2')
    assert vim['INTFMT'] == 'HIGH'

    assert vim['NS'] == 100
    assert vim['N1'] == 100
    assert vim['NL'] == 200
    assert vim['N2'] == 200
    assert vim['N3'] == 1
    assert vim['NBB'] == 0
    assert vim['NLB'] == 0
    assert vim['RECSIZE'] == 200


def test_vicarimage_binheader_from_scratch(rng: np.random.Generator) -> None:
    """binheader sets BREALFMT and NLB, and can be given as bytes or an array."""

    vim = VicarImage()
    vim.array = rng.integers(0, 32000, (200, 100)).astype('>i2')

    vim.binheader = rng.standard_normal((2, 100)).astype('>f4')
    assert vim['BREALFMT'] == 'IEEE'
    vim.binheader = rng.standard_normal((2, 100)).astype('<f4')
    assert vim['BREALFMT'] == 'RIEEE'
    vim.binheader = rng.standard_normal((2, 100)).astype('>f4')
    assert vim['BREALFMT'] == 'IEEE'
    assert vim['NLB'] == 4

    vim.binheader = None

    # The prefix must match the array's INTFMT
    with pytest.raises(VicarError):
        vim.prefix = rng.integers(0, 32000, (200, 10)).astype('<i2')

    vim.prefix = rng.integers(0, 32000, (200, 10)).astype('>i2')
    assert vim['NLB'] == 0
    assert vim['RECSIZE'] == 220

    vim.binheader = rng.standard_normal((2, 55)).astype('<f4')
    assert vim['BREALFMT'] == 'RIEEE'
    vim.binheader = rng.standard_normal((2, 55)).astype('>f4')
    assert vim['BREALFMT'] == 'IEEE'
    assert np.all(vim.binheader == vim.binheader_array(kind='f'))

    saved = vim.binheader
    vim.binheader = bytes(saved)
    array = vim.binheader_array(kind='f', size=4).reshape(2, 55)
    assert np.all(saved == array)

    vim.binheader = None
    assert vim.binheader_array() is None


def test_vicarimage_from_float_array(rng: np.random.Generator) -> None:
    """from_array() with floats sets REALFMT; a prefix may then set INTFMT."""

    vim = VicarImage.from_array(rng.standard_normal((3, 100, 100)).astype('>f8'))
    assert vim['REALFMT'] == 'IEEE'
    vim = VicarImage.from_array(rng.standard_normal((3, 100, 100)).astype('<f8'))
    assert vim['REALFMT'] == 'RIEEE'
    vim = VicarImage.from_array(rng.standard_normal((3, 100, 100)).astype('>f8'))
    assert vim['REALFMT'] == 'IEEE'
    assert vim['NB'] == 3
    assert vim['NL'] == 100
    assert vim['NS'] == 100
    assert vim['FORMAT'] == 'DOUB'

    # A single-byte prefix leaves INTFMT as it was
    vim.label['INTFMT'] = 'HIGH'
    vim.prefix = rng.integers(0, 255, (3, 100, 10)).astype('u1')
    assert vim['INTFMT'] == 'HIGH'

    vim.label['INTFMT'] = 'LOW'
    vim.prefix = rng.integers(0, 255, (3, 100, 10)).astype('u1')
    assert vim['INTFMT'] == 'LOW'

    vim.prefix = rng.integers(0, 32000, (3, 100, 10)).astype('>i2')
    assert vim['INTFMT'] == 'HIGH'
    vim.prefix = rng.integers(0, 32000, (3, 100, 10)).astype('<i2')
    assert vim['INTFMT'] == 'LOW'

    # A float prefix must match the array's REALFMT
    with pytest.raises(VicarError):
        vim.prefix = rng.standard_normal((3, 100, 100)).astype('<f8')

    vim.prefix = rng.standard_normal((3, 100, 100)).astype('>f4')
    assert vim['FORMAT'] == 'DOUB'     # unchanged


def test_vicarimage_from_int_array(rng: np.random.Generator) -> None:
    """from_array() with integers sets INTFMT; a prefix may then set REALFMT."""

    vim = VicarImage.from_array(rng.integers(-1000, 1000, (100, 100)).astype('<i4'))
    assert vim['INTFMT'] == 'LOW'
    vim = VicarImage.from_array(rng.integers(-1000, 1000, (100, 100)).astype('>i4'))
    assert vim['INTFMT'] == 'HIGH'
    vim = VicarImage.from_array(rng.integers(-1000, 1000, (100, 100)).astype('<i4'))
    assert vim['INTFMT'] == 'LOW'
    assert vim['NB'] == 1
    assert vim['NL'] == 100
    assert vim['NS'] == 100
    assert vim['FORMAT'] == 'FULL'

    vim.prefix = rng.standard_normal((100, 10)).astype('>f4')
    assert vim['REALFMT'] == 'IEEE'
    vim.prefix = rng.standard_normal((100, 10)).astype('<f4')
    assert vim['REALFMT'] == 'RIEEE'
    vim.prefix = rng.standard_normal((100, 10)).astype('>f4')
    assert vim['REALFMT'] == 'IEEE'

    # An integer prefix must match the array's INTFMT
    with pytest.raises(VicarError):
        vim.prefix = rng.integers(0, 32000, (100, 100)).astype('>i2')

    vim.prefix = rng.integers(0, 32000, (100, 100)).astype('<i2')
    assert vim['FORMAT'] == 'FULL'     # unchanged

##########################################################################################
