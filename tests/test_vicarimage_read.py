##########################################################################################
# tests/test_vicarimage_read.py
# Reading VICAR images, with and without overrides of the array, prefix, and binheader
##########################################################################################

from pathlib import Path

import numpy as np
import pytest
from filecache import FCPath

from vicar.vicarimage import VicarImage
from vicar.vicarlabel import VicarError


@pytest.fixture
def europa_path(data_dir: Path) -> Path:
    """Path to C0532836239R.IMG, a Galileo image with a prefix and binary header."""

    return data_dir / 'C0532836239R.IMG'


def test_vicarimage_read_label(europa_path: Path) -> None:
    """Label parameters are available by indexing and through as_dict()."""

    vim = VicarImage(europa_path)
    assert vim['NL'] == 800
    assert vim['TRUTH_WINDOW'] == [801, 801, 96, 96]
    assert vim['COMPRESSION_RATIO'] == 9.64155
    assert vim['SOLRANGE'] == 7.43341E+08
    assert vim['TARGET'] == 'EUROPA'
    assert vim.as_dict()['TARGET'] == 'EUROPA'


def test_vicarimage_read_array(europa_path: Path) -> None:
    """The image is available as 3-D and 2-D arrays under several names."""

    vim = VicarImage(europa_path)
    assert vim.array.shape == (1, 800, 800)
    assert vim.array3d.shape == (1, 800, 800)
    assert vim.data_3d.shape == (1, 800, 800)
    assert vim.array2d.shape == (800, 800)
    assert vim.data_2d.shape == (800, 800)

    image = vim.array2d
    assert image.dtype == np.dtype('uint8')
    assert image[367, 371] == 220


def test_vicarimage_read_binheader_and_prefix(europa_path: Path) -> None:
    """The binary header and prefix bytes are read along with the image."""

    vim = VicarImage(europa_path)
    assert vim['NLB'] == 6
    bh = vim.binheader_array(kind='u', size=2)
    assert bh.size == 6 * vim['RECSIZE'] / 2
    assert bh.dtype == np.dtype('<u2')

    assert vim['NBB'] == 200
    assert vim.prefix.shape == (1, 800, 200)
    assert vim.prefix_3d.shape == (1, 800, 200)
    assert vim.prefix3d.shape == (1, 800, 200)
    assert vim.prefix_2d.shape == (800, 200)
    assert vim.prefix2d.shape == (800, 200)


def test_vicarimage_from_file(europa_path: Path) -> None:
    """from_file() is equivalent to the constructor."""

    assert VicarImage(europa_path) == VicarImage.from_file(europa_path)


def test_vicarimage_from_file_extraneous(europa_path: Path,
                                         capsys: pytest.CaptureFixture[str]) -> None:
    """The extraneous option controls what happens to bytes after the image data."""

    with pytest.raises(VicarError):
        VicarImage.from_file(europa_path, extraneous='error')

    with pytest.warns(UserWarning, match='has 23488 zero-valued trailing bytes'):
        VicarImage.from_file(europa_path, extraneous='warn')

    extra = VicarImage.from_file(europa_path, extraneous='include')[-1]
    assert len(extra) == 23488
    assert all(c == 0 for c in extra)

    VicarImage.from_file(europa_path, extraneous='print')
    assert 'has 23488 zero-valued trailing bytes' in capsys.readouterr().out

    with pytest.raises(ValueError):
        VicarImage.from_file(europa_path, extraneous='???')


def test_vicarimage_filepath_property(europa_path: Path) -> None:
    """filepath can be cleared, and a str assigned to it is stored as an FCPath."""

    vim = VicarImage(europa_path)
    vim.filepath = None
    assert vim.filepath is None
    vim.filepath = str(europa_path)
    assert str(vim.filepath).replace('\\', '/') == str(europa_path).replace('\\', '/')
    assert isinstance(vim.filepath, FCPath)


def test_vicarimage_read_tabular(geoma_path: Path) -> None:
    """A tabular file has a binary header but no image or prefix."""

    test = VicarImage(geoma_path)
    assert test.array is None
    assert test.array2d is None
    assert test.array3d is None
    assert test.prefix is None
    assert test.prefix2d is None
    assert test.prefix3d is None

    array = test.binheader_array()
    assert array.shape == (552, 4)
    assert array.dtype == np.dtype('=f4')
    assert np.all(array[0] == np.array([25.11, 25.29, 24.076107, 11.095002],
                                       dtype='float32'))
    assert np.all(array[2] == np.array([20.33, 85.48, 14.932872, 57.43326],
                                       dtype='float32'))


def test_vicarimage_read_with_mismatched_overrides(europa_path: Path,
                                                   rng: np.random.Generator) -> None:
    """Overrides that do not fit the label's dimensions are rejected."""

    with pytest.raises(VicarError):
        VicarImage(europa_path, array=rng.standard_normal((100, 100)).astype('<f4'))

    with pytest.raises(VicarError):
        VicarImage(europa_path, prefix=rng.standard_normal((100, 100)).astype('<f4'))

    with pytest.raises(VicarError):
        VicarImage(europa_path, binheader=1999 * b'\0')

    # A new prefix changes RECSIZE, so the binheader no longer fits
    prefix = rng.standard_normal((800, 10)).astype('<f4')
    with pytest.raises(VicarError):
        VicarImage(europa_path, prefix=prefix)

    array = rng.integers(0, 255, (1, 800, 800)).astype('u1')
    with pytest.raises(VicarError):
        VicarImage(europa_path, array=array, prefix=prefix)


def test_vicarimage_read_with_overrides(europa_path: Path,
                                        rng: np.random.Generator) -> None:
    """The array, prefix, and binheader read from a file can each be replaced."""

    binheader = 2000 * b'\0'
    vim = VicarImage(europa_path, binheader=binheader)
    assert vim.binheader == binheader

    prefix = rng.standard_normal((800, 10)).astype('<f4')
    binheader = 840 * b'1'
    vim = VicarImage(europa_path, prefix=prefix, binheader=binheader)
    assert np.all(vim.prefix2d.view(dtype='<f4') == prefix)
    assert vim.binheader == binheader

    array = rng.integers(0, 255, (1, 800, 800)).astype('u1')
    vim = VicarImage(europa_path, array=array)
    assert np.all(vim.array == array)

    vim = VicarImage(europa_path, array=array, prefix=prefix, binheader=b'')
    assert np.all(vim.array == array)
    assert np.all(vim.prefix2d.view(dtype='<f4') == prefix)
    assert vim.binheader is None


def test_vicarimage_read_removing_overrides(europa_path: Path) -> None:
    """An empty prefix or binheader override removes it."""

    vim = VicarImage(europa_path, binheader=b'')
    assert vim.array.shape == (1, 800, 800)
    assert vim.prefix2d.shape == (800, 200)
    assert vim.binheader is None

    vim = VicarImage(europa_path, prefix=[], binheader=b'')
    assert vim.array.shape == (1, 800, 800)
    assert vim.prefix2d is None
    assert vim.binheader is None


@pytest.mark.parametrize(('filename', 'name', 'value'), [
    ('N1536633072_1_CALIB.IMG', 'UNEVEN_BIT_WEIGHT_CORRECTION_FLAG', 1),
    ('C0003061900R.IMG', 'BARC', 'IP\x80'),
])
def test_vicarimage_strict(data_dir: Path, filename: str, name: str, value: object) -> None:
    """Non-standard labels are rejected unless strict=False."""

    filepath = data_dir / filename
    with pytest.raises(VicarError):
        VicarImage(filepath)

    vim = VicarImage(filepath, strict=False)
    assert vim[name] == value

##########################################################################################
