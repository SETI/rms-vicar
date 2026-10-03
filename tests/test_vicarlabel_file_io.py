##########################################################################################
# tests/test_vicarlabel_file_io.py
# VicarLabel read_label(), write_label(), is_vicar_file(), and the filepath property
##########################################################################################

import os
import shutil
from pathlib import Path

import pytest
from filecache import FCPath

from vicar.vicarlabel import VicarLabel


@pytest.fixture
def geoma_copy(tmp_path: Path, geoma_path: Path) -> Path:
    """A scratch copy of C2069302_GEOMA.DAT that a test may overwrite."""

    dest = tmp_path / 'C2069302_GEOMA_new_label.DAT'
    shutil.copy(geoma_path, dest)
    return dest


def test_vicarlabel_write_label_shrinks(geoma_copy: Path) -> None:
    """Writing a shorter label removes the EOL label and truncates the file."""

    vic = VicarLabel(geoma_copy)
    for k in range(1, 11):
        del vic[f'LAB{k:02d}']
    vic.write_label(geoma_copy)

    altvic = VicarLabel(geoma_copy)
    assert vic == altvic
    assert len(vic['LBLSIZE+']) == 1
    assert os.path.getsize(geoma_copy) == vic['LBLSIZE'] + vic['RECSIZE'] * vic['NLB']
    assert altvic.filepath == geoma_copy


def test_vicarlabel_write_label_grows(geoma_copy: Path, geoma_label: str) -> None:
    """Writing a longer label to the object's own file restores the EOL label."""

    vic = VicarLabel(geoma_copy)
    for k in range(1, 11):
        del vic[f'LAB{k:02d}']
    vic.write_label(geoma_copy)

    original = VicarLabel(geoma_label)
    for k in range(1, 11):
        vic[f'LAB{k:02d}'] = original[f'LAB{k:02d}']
    vic.write_label()

    altvic = VicarLabel(geoma_copy)
    assert vic == altvic
    assert len(vic['LBLSIZE+']) == 2
    assert os.path.getsize(geoma_copy) == (vic['LBLSIZE'] + vic['RECSIZE'] * vic['NLB']
                                           + vic[('LBLSIZE', 1)])


def test_vicarlabel_write_label_other_file(geoma_copy: Path, tmp_path: Path) -> None:
    """write_label(filepath) writes to that file, not the one the label came from."""

    dest2 = tmp_path / 'C2069302_GEOMA_new_label2.DAT'
    shutil.copy(geoma_copy, dest2)

    vic = VicarLabel(geoma_copy)
    del vic['LAB01']
    vic.write_label(dest2)
    assert VicarLabel(dest2) == vic
    assert 'LAB01' in VicarLabel(geoma_copy)


def test_vicarlabel_write_label_without_filepath(geoma_path: Path) -> None:
    """write_label() with no filepath requires one to be associated with the label."""

    vic = VicarLabel(geoma_path)
    vic.filepath = None
    with pytest.raises(ValueError):
        vic.write_label()


def test_vicarlabel_filepath_property(geoma_path: Path) -> None:
    """Assigning a str to filepath stores an FCPath."""

    vic = VicarLabel(geoma_path)
    vic.filepath = str(geoma_path)
    assert isinstance(vic.filepath, FCPath)
    assert str(vic.filepath).replace('\\', '/') == str(geoma_path).replace('\\', '/')


@pytest.mark.parametrize('convert', [Path, str, FCPath])
def test_vicarlabel_is_vicar_file(data_dir: Path, convert: type) -> None:
    """VICAR files are recognized whether given as a Path, str, or FCPath."""

    assert VicarLabel.is_vicar_file(convert(data_dir / 'C2069302_GEOMA.DAT'))
    assert VicarLabel.is_vicar_file(convert(data_dir / 'C2069302_RAW.IMG'))


@pytest.mark.parametrize('content', [b'', b'LBLSIZE', b'LBLSIZEX=1536', b'Hello, world!'])
def test_vicarlabel_is_vicar_file_false(tmp_path: Path, content: bytes) -> None:
    """A file that does not begin with a valid LBLSIZE keyword is not a VICAR file."""

    not_vicar = tmp_path / 'not_vicar.txt'
    not_vicar.write_bytes(content)
    assert not VicarLabel.is_vicar_file(not_vicar)


def test_vicarlabel_is_vicar_file_missing(tmp_path: Path) -> None:
    """A missing file raises OSError rather than returning False."""

    with pytest.raises(OSError):
        VicarLabel.is_vicar_file(tmp_path / 'missing.IMG')


def test_vicarlabel_read_image_file(data_dir: Path) -> None:
    """The label of an image file is read with its parameter values and formats."""

    filepath = data_dir / 'C0532836239R.IMG'
    vic = VicarLabel(filepath)

    assert vic.filepath == filepath
    assert vic['NL'] == 800
    assert vic['TRUTH_WINDOW'] == [801, 801, 96, 96]
    assert vic['COMPRESSION_RATIO'] == 9.64155
    assert vic['SOLRANGE'] == 7.43341E+08
    assert vic['TARGET'] == 'EUROPA'


def test_vicarlabel_read_label(data_dir: Path) -> None:
    """read_label() returns the label string from a path or an open file."""

    filepath = data_dir / 'C0532836239R.IMG'
    vic = VicarLabel(filepath)

    test = VicarLabel.read_label(filepath)
    assert vic == VicarLabel(test)

    with filepath.open('rb') as f:
        assert VicarLabel.read_label(f) == test


def test_vicarlabel_read_label_extra(data_dir: Path) -> None:
    """read_label(_extra=True) also returns the bytes that follow the image data."""

    filepath = data_dir / 'C0532836239R.IMG'
    vic = VicarLabel(filepath)

    (test, extra) = VicarLabel.read_label(filepath, _extra=True)
    assert test == VicarLabel.read_label(filepath)
    size = vic['LBLSIZE'] + (vic['NL'] + vic['NLB']) * vic['RECSIZE']
    assert size + len(extra) == os.path.getsize(filepath)
    assert all(c == 0 for c in extra)

##########################################################################################
