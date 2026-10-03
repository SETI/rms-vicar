##########################################################################################
# tests/test_vicarlabel_construct.py
# VicarLabel construction from dicts, tuples, and strings, and rejection of bad input
##########################################################################################

from typing import Any

import pytest

from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR
from vicar.vicarlabel import VicarError, VicarLabel, _REQUIRED


def test_vicarlabel_empty() -> None:
    """An empty label holds exactly the required parameters."""

    assert len(VicarLabel()) == len(_REQUIRED)


@pytest.mark.parametrize('source', [
    {'SEVEN': (7.,)},
    {'SEVEN': (7., '')},
    {'SEVEN': 7.},
])
def test_vicarlabel_single_parameter(source: dict[str, Any]) -> None:
    """A single tuple and the equivalent dicts produce the same label."""

    almost_empty = VicarLabel(('SEVEN', 7.0))
    assert len(almost_empty) == len(_REQUIRED) + 1
    assert almost_empty == VicarLabel(source)


def test_vicarlabel_append(geoma_label: str) -> None:
    """A label built in two appended pieces equals the whole."""

    reference = VicarLabel(geoma_label)
    parts = geoma_label.partition('LBLSIZE=1024')
    vic2 = VicarLabel(parts[0])
    vic2.append(parts[1] + parts[2])
    assert reference == vic2

    vic3 = vic2.copy()
    vic2.append('PI=3.14159')
    vic3.append([('PI', 3.14159)])
    assert vic2 == vic3


def test_vicarlabel_append_dict() -> None:
    """append() accepts a dict, whose tuple values carry formats."""

    lbl = VicarLabel()
    lbl.append({'A': 1, 'B': 'TWO', 'C': (3, '%03d', 1, 1)})
    assert lbl['A'] == 1
    assert lbl['B'] == 'TWO'
    assert lbl['C'] == 3
    assert lbl._formats[-1] == ('%03d', 0, 1, 1, [])


def test_vicarlabel_missing_lblsize(geoma_label: str) -> None:
    """A missing LBLSIZE is inserted at the front with a value of zero."""

    parts = geoma_label.partition('LBLSIZE=1024')
    params = _LABEL_GRAMMAR.parse_string(parts[0]).as_list()
    missing_lblsize = VicarLabel(params[1:])
    assert missing_lblsize.names()[0] == 'LBLSIZE'
    assert missing_lblsize['LBLSIZE'] == 0

    missing_lblsize[0] = (1536, 12)
    missing_lblsize.append(parts[1] + parts[2])
    assert VicarLabel(geoma_label) == missing_lblsize


def test_vicarlabel_lblsize_moved_to_front() -> None:
    """LBLSIZE is moved to the front of a label that has it elsewhere."""

    vic = VicarLabel("FORMAT='BYTE'  SEVEN=7.0  LBLSIZE=100  MORE='LESS'")
    assert vic.items()[0] == ('LBLSIZE', 100)


@pytest.mark.parametrize(('source', 'error'), [
    ("FORMAT='BYTE'  SEVEN=7.0  LBLSIZE=100  MORE=xyz", VicarError),
    ({1, 2, 3}, TypeError),
    ([('LBLSIZE', 100), set()], TypeError),
    ([('LBLSIZE', 100), ('RECSIZE',)], TypeError),
    ([('LBLSIZE', 100), 'RECSIZE'], TypeError),
    ([('LBLSIZE', 100), ('TWO', 2., '', 4, 5, 6, 7)], VicarError),
    ([('LBLSIZE', 100), ('TWO', 2., 3, 4, 5, 6)], VicarError),
    ([('LBLSIZE', 100), ('TWO', 2., 3, '')], VicarError),
    ([('LBLSIZE', 100), (1, 2.)], VicarError),
    ([('LBLSIZE', 100), ('TWo', 2.)], VicarError),
    ([('LBLSIZE', 100), ('CR', '\n')], VicarError),
    ([('LBLSIZE', 100), ('LIST1', [])], VicarError),
    ([('LBLSIZE', 100), ('LIST2', [1, 2.])], VicarError),
    ([('LBLSIZE', 100), ('SET', set())], VicarError),
    ([('LBLSIZE', 100), ('SET', [set()])], VicarError),
    ([('A23456789012345678901234567890123', 7)], VicarError),
])
def test_vicarlabel_invalid_source(source: Any, error: type[Exception]) -> None:
    """Invalid names, values, and tuple shapes are rejected."""

    with pytest.raises(error):
        VicarLabel(source)


def test_vicarlabel_strict_false() -> None:
    """strict=False accepts values that break the VICAR standard but are representable."""

    VicarLabel([('A2345678901234567890123456789012', 7)])
    VicarLabel([('LBLSIZE', 100), ('TWo', 2.), ('CR', '\n'), ('LIST1', []),
                ('LIST2', [1, 2.]), ('A23456789012345678901234567890123', 7)],
               strict=False)
    with pytest.raises(VicarError):
        VicarLabel([('LBLSIZE', 100), ('SET', [1, 2, set()])], strict=False)


@pytest.mark.parametrize(('value', 'fmt'), [
    (4, '%.4f'),
    (4, '%.4g'),
    (4, '%.4e'),
    (4., '%4d'),
    (4., '%4i'),
    ('abc', '%4i'),
    ('abc', '%s'),
])
def test_vicarlabel_invalid_format(value: Any, fmt: str) -> None:
    """A format that does not match the value type raises TypeError."""

    with pytest.raises(TypeError):
        VicarLabel([('ABC', value, fmt)])
    with pytest.raises(TypeError):
        VicarLabel([('ABC', [(value, fmt)])])


def test_vicarlabel_invalid_list_format() -> None:
    """A list element with too many formatting hints raises VicarError."""

    with pytest.raises(VicarError):
        VicarLabel([('ABC', [(7, '%02d', 1, 2, 3)])])

##########################################################################################
