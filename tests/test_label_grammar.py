##########################################################################################
# tests/test_label_grammar.py
# Tests of the pyparsing grammar that splits a VICAR label into parameter tuples
##########################################################################################

from typing import Any

import pytest
from pyparsing import ParseException

from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR


def _parse(text: str) -> list[Any]:
    return list(_LABEL_GRAMMAR.parse_string(text).as_list())


def test_label_grammar_strings_and_padding() -> None:
    """Blanks around '=' are recorded and trailing nulls are ignored."""

    text = "LBLSIZE=1536  FORMAT   = 'BYTE'   \0\0"
    assert _parse(text) == [('LBLSIZE', 1536), ('FORMAT', 'BYTE', 3, 1, 3)]


def test_label_grammar_integer_formats() -> None:
    """Leading zeros and explicit signs are preserved as a format string."""

    text = "A=0  B=00  C=+0  D=+1  E=-1  F=-01  G=+01  "
    assert _parse(text) == [('A', 0),
                            ('B', 0, '%02d'),
                            ('C', 0, '%+d'),
                            ('D', 1, '%+d'),
                            ('E', -1),
                            ('F', -1, '%03d'),
                            ('G', 1, '%+03d')]


def test_label_grammar_real_formats() -> None:
    """The number of digits in a real value is preserved as a format string."""

    text = "TBPPXL=0.0  INA=77.7883  SOLRANGE=7.43341e+08  "
    assert _parse(text) == [('TBPPXL', 0., '%#.1f'),
                            ('INA', 77.7883, '%#.4f'),
                            ('SOLRANGE', 7.43341e+08, '%#.5E')]


def test_label_grammar_exponent_forms() -> None:
    """Fortran 'D' exponents and bare decimal points parse as floats."""

    text = "A=1D5  B=+1d4  C=2.E2  D=.1e1  E=+.1e1  "
    tuples = _parse(text)
    assert tuples == [('A', 100000., '%#.0E'),
                      ('B', 10000., '%#+.0E'),
                      ('C', 200., '%#.0E'),
                      ('D', 1., '%#.0E'),
                      ('E', 1., '%#+.0E')]
    for t in tuples:
        assert isinstance(t[1], float)


def test_label_grammar_integer_list() -> None:
    """Blanks and formats of individual list elements are recorded."""

    text = "DIGITS=(1, 2,03 , 004 )  "
    assert _parse(text) == [('DIGITS', [1, (2, 1, 0), (3, '%02d', 1), (4, '%03d', 1, 1)])]


@pytest.mark.parametrize(('text', 'expected'), [
    ("GROUPS=('LINE','SAMP','C_POS_IMAGE','INPUT')  ",
     ('GROUPS', ['LINE', 'SAMP', 'C_POS_IMAGE', 'INPUT'])),
    ("GROUPS=('LINE', 'SAMP' ,'C_POS_IMAGE','INPUT')  ",
     ('GROUPS', ['LINE', ('SAMP', 1, 1), 'C_POS_IMAGE', 'INPUT'])),
    ("GROUPS   =('LINE','SAMP','C_POS_IMAGE','INPUT')  ",
     ('GROUPS', ['LINE', 'SAMP', 'C_POS_IMAGE', 'INPUT'], 3, 0, 2)),
    ("GROUPS=   ('LINE','SAMP','C_POS_IMAGE','INPUT')  ",
     ('GROUPS', ['LINE', 'SAMP', 'C_POS_IMAGE', 'INPUT'], 3, 2)),
])
def test_label_grammar_string_list(text: str, expected: tuple[Any, ...]) -> None:
    """A parenthesized list of strings becomes a Python list."""

    tuples = _parse(text)
    assert tuples == [expected]
    assert isinstance(tuples[0][1], list)


def test_label_grammar_long_name() -> None:
    """Names longer than the VICAR limit of 32 characters are accepted."""

    text = 'A2345678901234567890123456789012=7'
    assert _parse(text) == [('A2345678901234567890123456789012', 7, 0)]


@pytest.mark.parametrize('text', [
    '_123=7',                                               # leading underscore
    "GROUPS=('LINE','SAMP','C_POS_IMAGE','INPUT',)  ",      # trailing comma
])
def test_label_grammar_invalid(text: str) -> None:
    """Malformed labels raise ParseException."""

    with pytest.raises(ParseException):
        _LABEL_GRAMMAR.parse_string(text)

##########################################################################################
