##########################################################################################
# tests/test_vicarlabel_setitem.py
# VicarLabel __setitem__ validation, value formatting, copy(), and reorder()
##########################################################################################

from typing import Any

import pytest

from vicar.vicarlabel import VicarError, VicarLabel


def _label() -> VicarLabel:
    return VicarLabel("FORMAT='BYTE'  SEVEN=7.0  LBLSIZE=100  MORE='LESS'")


@pytest.mark.parametrize(('key', 'value', 'error'), [
    ('_INVALID_NAME', 1, VicarError),
    ('TUPLE', [], VicarError),              # no empty lists
    ('SET', set(), VicarError),
    ('LIST', [1, 2.], VicarError),
    ('LIST', [1., 'TWO'], VicarError),
    ('LIST', ['ONE', set()], VicarError),
    ('LIST', [set(), 2], VicarError),
    (set(), 7, TypeError),
    (3.14, 'pi', TypeError),
    (0, set(), VicarError),
    ('ORG', 'whatever', VicarError),
    ('NL', 'whatever', VicarError),
    ('NL', -1, VicarError),
])
def test_vicarlabel_setitem_invalid(key: Any, value: Any, error: type[Exception]) -> None:
    """Invalid names, values, and values of required parameters are rejected."""

    vic = _label()
    with pytest.raises(error):
        vic[key] = value


# Each case is a sequence of (value assigned, value_str() afterward). Assigning a bare
# value keeps the existing format if it still applies, and replaces it otherwise.
_VALUE_STR_SEQUENCES = {
    'int': [
        (1, '1'),
        ((1, '%+03d'), '+01'),
        (3, '+03'),                         # format preserved
        ((1, '%+03d', 3), '+01   '),
        (4, '+04   '),
        (4., '4.   '),                      # format replaced
        (4, '4   '),
        ((1, '%+03d', 3, 0), '   +01'),
        (4, '   +04'),
        ((1, 3, 0), '   1'),
        (4, '   4'),
        ((1, 3), '1   '),
        (4, '4   '),
    ],
    'real': [
        (1.234, '1.234'),
        ((1.234, '%#+.4f'), '+1.2340'),
        (1.23456, '+1.2346'),               # format preserved
        ((1.234, '%#.0f'), '1.'),
        (1.23456, '1.'),
        ((1.234, '%#+.4f', 3), '+1.2340   '),
        (1.23456, '+1.2346   '),
        (1, '1   '),                        # format replaced
        (1.23456, '1.23456   '),            # format replaced
        ((1.234, '%#+.4f', 3, 0), '   +1.2340'),
        (1.23456, '   +1.2346'),
        ((1.234, 3, 0), '   1.234'),
        (1.23456, '   1.23456'),
        ((1.234, 3), '1.234   '),
        (1.23456, '1.23456   '),
    ],
    'real_rounding': [
        (1.234999993535, '1.235'),
        (-1.23500000123, '-1.235'),
        (1.000001999999, '1.'),
        (-1.9999900000, '-2.'),
        (9.9999900000, '10.'),
        (1.899999050000044, '1.9'),
        (-1.02999998434, '-1.03'),
    ],
    'real_whole': [
        (7., '7.'),
    ],
    'real_exponent': [
        (-1.234999993535e-12, '-1.235E-12'),
        (1.23500000123e-12, '1.235E-12'),
        (-1.000001999999e-12, '-1.E-12'),
        (1.9999900000e-12, '2.E-12'),
        (-9.9999900000e-12, '-1.E-11'),
        (1.899999050000044e-12, '1.9E-12'),
        (-1.02999998434e-12, '-1.03E-12'),
    ],
    'real_list': [
        ([1.234, -1.234999993535e-12], '(1.234,-1.235E-12)'),
        ([(1.234, '%#+.4f'), -1.23500000123, -1.000001999999e-12],
         '(+1.2340,-1.235,-1.E-12)'),
        ([(1.234, 1, 0), (7., 1), -1.02999998434e-12], '( 1.234,7. ,-1.03E-12)'),
        (([(1.234, 1, 0), (7., 1), -1.02999998434e-12], 2, 3),
         '  ( 1.234,7. ,-1.03E-12)   '),
    ],
    'string': [
        ('xyz', "'xyz'"),
        (('xyz', 3), "'xyz'   "),
        ('abc', "'abc'   "),
        (('abc', 3, 1), "   'abc' "),
        ('xyz', "   'xyz' "),
    ],
    'int_list': [
        ([1, 2, 3], '(1,2,3)'),
        (([1, 2, 3], 2, 1), '  (1,2,3) '),
        ([4, 5, 6, 7], '  (4,5,6,7) '),
        ([(1, 1, 1), (2, 2, 2), (3, 3, 3)], '( 1 ,  2  ,   3   )'),
        ([4, 5, 6, 7], '(4,5,6,7)'),
        (([(1, 1, 1), (2, 2, 2), (3, 3, 3)], 2, 1), '  ( 1 ,  2  ,   3   ) '),
        ([4, 5, 6, 7], '  (4,5,6,7) '),
    ],
}


@pytest.mark.parametrize('sequence', _VALUE_STR_SEQUENCES.values(),
                         ids=_VALUE_STR_SEQUENCES.keys())
def test_vicarlabel_value_str(sequence: list[tuple[Any, str]]) -> None:
    """value_str() reflects the format given with, or kept from, each assignment."""

    vic = _label()
    for value, expected in sequence:
        vic['X'] = value
        assert vic.value_str('X') == expected, value


def test_vicarlabel_value_str_by_occurrence() -> None:
    """A second occurrence of a required parameter is not validated."""

    vic = _label()
    vic['ORG+'] = 'not BSQ or BIL or BIP'   # not a VicarError
    assert vic.value_str(('ORG', -1)) == "'not BSQ or BIL or BIP'"


def _label_with_letters() -> VicarLabel:
    vic = _label()
    for name in 'ABCDEFGH':
        vic[name] = 7.
    return vic


def test_vicarlabel_copy() -> None:
    """A copy is equal to, but independent of, the original."""

    vic = _label_with_letters()
    vic2 = vic.copy()
    assert vic == vic2

    vic2['E'] = 9.
    assert vic['E'] == 7.
    vic2['NEW_ITEM'] = 'This is a new item'
    assert len(vic) == len(vic2) - 1


def test_vicarlabel_reorder() -> None:
    """reorder() moves parameters to follow the first name given."""

    vic = _label_with_letters()
    vic.reorder('', 'A', 'B', 'C', 'F')
    assert vic.names()[:6] == ['LBLSIZE', 'A', 'B', 'C', 'F', 'FORMAT']

    vic.reorder('FORMAT', 'F', 'G')
    assert vic.names()[:7] == ['LBLSIZE', 'A', 'B', 'C', 'FORMAT', 'F', 'G']


@pytest.mark.parametrize(('names', 'error'), [
    (('A', 'UNK', 'C', 'F'), KeyError),
    (('A', 'F', 'C', 'F'), ValueError),
])
def test_vicarlabel_reorder_invalid(names: tuple[str, ...],
                                    error: type[Exception]) -> None:
    """reorder() rejects unknown and duplicated names."""

    vic = _label_with_letters()
    with pytest.raises(error):
        vic.reorder(*names)


@pytest.mark.parametrize(('org', 'n321_order', 'nbls_order'), [
    ('BSQ', ('NB', 'NL', 'NS'), ('N3', 'N2', 'N1')),
    ('BIL', ('NL', 'NB', 'NS'), ('N2', 'N3', 'N1')),
    ('BIP', ('NL', 'NS', 'NB'), ('N1', 'N3', 'N2')),
])
def test_vicarlabel_dimensions(org: str, n321_order: tuple[str, str, str],
                               nbls_order: tuple[str, str, str]) -> None:
    """N1-N3 and NB, NL, NS are kept consistent according to ORG."""

    vic = _label()
    vic['ORG'] = org

    vic._set_n321(300, 200, 100)
    assert (vic['N3'], vic['N2'], vic['N1']) == (300, 200, 100)
    assert tuple(vic[n] for n in n321_order) == (300, 200, 100)

    vic._set_nbls(101, 201, 301)
    assert (vic['NB'], vic['NL'], vic['NS']) == (101, 201, 301)
    assert tuple(vic[n] for n in nbls_order) == (101, 201, 301)

##########################################################################################
