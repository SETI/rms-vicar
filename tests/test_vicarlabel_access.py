##########################################################################################
# tests/test_vicarlabel_access.py
# VicarLabel indexing, membership, and iteration, checked against every source type
##########################################################################################

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR
from vicar.vicarlabel import VicarLabel


_GROUPS = [('GROUP_1', [3, 1]),
           ('GROUP_2', [4, 2]),
           ('GROUP_3', [3, 4, 1, 2]),
           ('GROUP_4', [3, 4]),
           ('GROUP_5', [1, 2, 3, 4]),
           ('GROUP_6', [3, 4, 1, 2]),
           ('GROUP_7', [1, 2, 3, 4]),
           ('GROUP_8', [1, 2, 3, 4]),
           ('GROUP_9', [1, 2]),
           ('GROUP_10', [1, 2, 3, 4]),
           ('GROUP_11', [3, 4, 1, 2])]


@pytest.fixture(params=['text', 'path', 'str', 'file', 'tuples'])
def vic(request: pytest.FixtureRequest, geoma_label: str,
        geoma_path: Path) -> Iterator[Any]:
    """The GEOMA label, constructed from each kind of source VicarLabel accepts."""

    match request.param:
        case 'text':
            yield VicarLabel(geoma_label)
        case 'path':
            yield VicarLabel(geoma_path)
        case 'str':
            yield VicarLabel(str(geoma_path))
        case 'file':
            with open(geoma_path, 'rb') as f:
                yield VicarLabel(f)
        case 'tuples':
            yield VicarLabel(_LABEL_GRAMMAR.parse_string(geoma_label).as_list())


def test_vicarlabel_getitem(vic: Any) -> None:
    """Values are retrieved by name, (name, occurrence), and numeric index."""

    assert vic['LBLSIZE'] == 1536
    assert vic[('LBLSIZE', 0)] == 1536
    assert vic[('LBLSIZE', 1)] == 1024
    assert vic[('LBLSIZE', -1)] == 1024
    assert vic[('LBLSIZE', -2)] == 1536
    assert vic['LBLSIZE+'] == [1536, 1024]
    assert vic[0] == 1536
    assert vic[-2] == 'SHOWALTER'


@pytest.mark.parametrize(('key', 'error'), [
    ('FOO', KeyError),
    ('FOO+', KeyError),
    (3.14159, TypeError),
    (('LBLSIZE', 2), IndexError),
    (set(), TypeError),
    (999, IndexError),
])
def test_vicarlabel_getitem_invalid(vic: Any, key: Any, error: type[Exception]) -> None:
    """Missing or malformed keys raise the matching exception."""

    with pytest.raises(error):
        vic[key]


def test_vicarlabel_contains(vic: Any) -> None:
    """Membership tests accept names and (name, occurrence) tuples."""

    assert 'LBLSIZE' in vic
    assert ('LBLSIZE', 0) in vic
    assert ('LBLSIZE', 1) in vic
    assert ('LBLSIZE', 2) not in vic
    assert ('LBLSIZE', -1) in vic
    assert ('LBLSIZE', -3) not in vic
    assert 'FOO' not in vic


def test_vicarlabel_get_and_len(vic: Any) -> None:
    """get() falls back to the default only when the key is missing."""

    assert vic.get('LBLSIZE', -1) == 1536
    assert vic.get(('LBLSIZE', 0), -1) == 1536
    assert vic.get(('LBLSIZE', 1), -1) == 1024
    assert vic.get(('LBLSIZE', 2), -1) == -1
    assert len(vic) == 71


def test_vicarlabel_arg(vic: Any) -> None:
    """arg() converts a key to its numeric index."""

    assert vic.arg('LBLSIZE') == 0
    assert vic.arg('DIM') == 4
    assert vic.arg(('LBLSIZE', 1)) == 57
    assert vic.arg(0) == 0
    assert vic.arg(4) == 4
    assert vic.arg(-1) == 70
    assert vic.arg(-71) == 0


@pytest.mark.parametrize(('key', 'error'), [
    (71, IndexError),
    (-72, IndexError),
    (('LBLSIZE', 2), IndexError),
    (('FOO', 0), KeyError),
])
def test_vicarlabel_arg_invalid(vic: Any, key: Any, error: type[Exception]) -> None:
    """arg() rejects out-of-range indices and unknown names."""

    with pytest.raises(error):
        vic.arg(key)


def test_vicarlabel_iterators(vic: Any) -> None:
    """names(), keys(), values(), and items() filter by name or regular expression."""

    assert list(vic)[:3] == [('LBLSIZE', 0), 'FORMAT', ('TYPE', 0)]

    assert list(vic.names('TASK')) == ['TASK', 'TASK', 'TASK']
    assert list(vic.names())[:3] == ['LBLSIZE', 'FORMAT', 'TYPE']

    assert list(vic.keys('TASK')) == [('TASK', 0), ('TASK', 1), ('TASK', 2)]
    assert list(vic.keys())[:3] == [('LBLSIZE', 0), 'FORMAT', ('TYPE', 0)]

    assert list(vic.values('TASK')) == ['TASK', 'VGRFILLI', 'RESLOC']
    assert list(vic.values())[:3] == [1536, 'BYTE', 'TABULAR']

    assert list(vic.items('TASK', unique=False)) == [('TASK', 'TASK'),
                                                     ('TASK', 'VGRFILLI'),
                                                     ('TASK', 'RESLOC')]
    assert list(vic.items('TASK', unique=True)) == [(('TASK', 0), 'TASK'),
                                                    (('TASK', 1), 'VGRFILLI'),
                                                    (('TASK', 2), 'RESLOC')]
    assert list(vic.items(unique=False))[:3] == [('LBLSIZE', 1536), ('FORMAT', 'BYTE'),
                                                 ('TYPE', 'TABULAR')]
    assert list(vic.items(unique=True))[:3] == [(('LBLSIZE', 0), 1536),
                                                ('FORMAT', 'BYTE'),
                                                (('TYPE', 0), 'TABULAR')]

    assert list(vic.items(r'GROUP_\d+')) == _GROUPS
    assert list(vic.values(r'GROUP_\d+')) == [g[1] for g in _GROUPS]
    assert list(vic.args(r'GROUP_\d+')) == list(range(31, 42))
    assert list(vic.args()) == list(range(71))


def test_vicarlabel_file_object_left_open(geoma_path: Path) -> None:
    """Reading from an open file does not close it."""

    with open(geoma_path, 'rb') as f:
        VicarLabel(f)
        assert not f.closed
    assert f.closed


def test_vicarlabel_equal_across_sources(geoma_label: str, geoma_path: Path) -> None:
    """Every source type yields the same label."""

    reference = VicarLabel(geoma_label)
    assert reference == VicarLabel(geoma_path)
    assert reference == VicarLabel(str(geoma_path))
    assert reference == VicarLabel.from_file(geoma_path)
    assert reference == VicarLabel(_LABEL_GRAMMAR.parse_string(geoma_label).as_list())
    assert reference != set()

##########################################################################################
