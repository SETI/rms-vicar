##########################################################################################
# tests/test_vicarlabel_keys.py
# VicarLabel extended keys: (name, occurrence), "NAME+", and (name, after_name, value)
##########################################################################################

from typing import Any

import pytest

from vicar.vicarlabel import VicarError, VicarLabel


def test_vicarlabel_setitem_occurrence() -> None:
    """(name, 0) and "NAME+" keys create parameters; (name, 1) appends a second."""

    lbl = VicarLabel()
    lbl['NEW1', 0] = 1
    lbl['NEW2+', 0] = 2
    lbl['NEW3', 0] = 3
    lbl['NEW4+', 0] = 4
    lbl['NEW5'] = 5
    lbl['NEW5', 1] = 6
    assert lbl['NEW1'] == 1
    assert lbl['NEW2'] == 2
    assert lbl['NEW3'] == 3
    assert lbl['NEW4'] == 4
    assert lbl['NEW5+'] == [5, 6]


@pytest.mark.parametrize('key', [('NEW6', 1), ('NEW6', -2)])
def test_vicarlabel_setitem_occurrence_invalid(key: tuple[str, int]) -> None:
    """A new parameter cannot be created at an occurrence other than 0 or -1."""

    lbl = VicarLabel()
    with pytest.raises(KeyError):
        lbl[key] = 7


@pytest.fixture
def lbl() -> Any:
    """A label with three TASK blocks, each followed by FOO and/or BAR."""

    lbl = VicarLabel()
    lbl.append({'TASK': 'FICOR77', 'FOO': 1})
    lbl.append({'TASK': 'RESLOC', 'BAR': 2})
    lbl.append({'TASK': 'GEOMA', 'FOO': 3, 'BAR': 4})
    return lbl


def test_vicarlabel_arg_with_value(lbl: Any) -> None:
    """arg(key, value) finds the occurrence of key that has the given value."""

    assert lbl.arg('TASK', 'GEOMA') == len(lbl) - 3
    assert lbl.arg('TASK', 'FICOR77') == len(lbl) - 7
    assert lbl.arg(len(lbl) - 3, 'GEOMA') == len(lbl) - 3

    with pytest.raises(ValueError):
        lbl.arg('TASK', 'whatever')
    with pytest.raises(ValueError):
        lbl.arg(len(lbl) - 3, 'RESLOC')


def test_vicarlabel_arg_after_key(lbl: Any) -> None:
    """arg((name, after_name, after_value)) finds name after a given parameter."""

    assert lbl.arg(('FOO', 'TASK', 'FICOR77'), 1) == len(lbl) - 6
    assert lbl.arg(('BAR', 'TASK', 'RESLOC'), 2) == len(lbl) - 4
    assert lbl.arg(('FOO', 'TASK', 'GEOMA'), 3) == len(lbl) - 2
    assert lbl.arg(('BAR', 'TASK', 'GEOMA'), 4) == len(lbl) - 1

    assert lbl.arg(('FOO', 'TASK', 'FICOR77')) == len(lbl) - 6
    assert lbl.arg(('BAR', 'TASK', 'RESLOC')) == len(lbl) - 4
    assert lbl.arg(('FOO', 'TASK', 'GEOMA')) == len(lbl) - 2
    assert lbl.arg(('BAR', 'TASK', 'GEOMA')) == len(lbl) - 1

    with pytest.raises(ValueError):
        lbl.arg(('FOO', 'TASK', 'GEOMA'), 99)
    with pytest.raises(KeyError):
        lbl.arg(('FOO', 'TASK', 'RESLOC'))


def test_vicarlabel_getitem_after_key(lbl: Any) -> None:
    """lbl[name, after_name, after_value] returns the matching value."""

    assert lbl['FOO', 'TASK'] == 1
    assert lbl['FOO', 'TASK', 'FICOR77'] == 1
    assert lbl['BAR', 'TASK', 'RESLOC'] == 2
    assert lbl['FOO', 'TASK', 'GEOMA'] == 3
    assert lbl['BAR', 'TASK', 'GEOMA'] == 4


@pytest.mark.parametrize(('key', 'error'), [
    (('BAR', 'TASK'), KeyError),
    (('BAR', 'TASK', 'FICOR77'), KeyError),
    (('FOO', 'TASK', 'RESLOC'), KeyError),
    (('FOO', 'TASKX'), KeyError),
    (('FOO', 'TASKX', 'whatever'), KeyError),
    (('FOO', 'TASK', 'RESSAR77'), ValueError),
])
def test_vicarlabel_getitem_after_key_invalid(lbl: Any, key: tuple[str, ...],
                                              error: type[Exception]) -> None:
    """A parameter missing after the given key raises KeyError; a missing value,
    ValueError."""

    with pytest.raises(error):
        lbl[key]


def test_vicarlabel_get_missing() -> None:
    """get() returns the default for a missing name, a list for "NAME+"."""

    test = VicarLabel()
    assert test.get('FOO', 7) == 7
    assert test.get('FOO+', 7) == [7]
    assert test.get(set(), 7) == 7


def test_vicarlabel_setitem_after_key_existing(lbl: Any) -> None:
    """Assigning to an existing (name, after_name, after_value) replaces its value."""

    lbl['FOO', 'TASK', 'FICOR77'] = 77
    assert lbl['FOO', 'TASK', 'FICOR77'] == 77
    assert lbl[len(lbl) - 6] == 77

    lbl['FOO', 'TASK', 'GEOMA'] = 88
    assert lbl['FOO', 'TASK', 'GEOMA'] == 88
    assert lbl[len(lbl) - 2] == 88

    lbl['FOO+', 'TASK', 'GEOMA'] = 33
    assert lbl['FOO+', 'TASK', 'GEOMA'] == [88, 33]
    del lbl['FOO', 'TASK', 'GEOMA']
    assert lbl['FOO+', 'TASK', 'GEOMA'] == [33]


def test_vicarlabel_contains_integer(lbl: Any) -> None:
    """An integer key is in the label if it is a valid index."""

    assert -len(lbl) in lbl
    assert len(lbl) - 1 in lbl
    assert -len(lbl) - 1 not in lbl
    assert len(lbl) not in lbl


def test_vicarlabel_contains_after_key(lbl: Any) -> None:
    """(name, after_name[, after_value]) is in the label if the name follows it."""

    assert 'FOO' in lbl
    assert ('FOO', 'TASK') in lbl
    assert ('FOO', 'TASK', 'FICOR77') in lbl
    assert ('FOO', 'TASK', 'RESLOC') not in lbl
    assert ('FOO', 'TASK', 'GEOMA') in lbl

    assert ('BAR', 'TASK') not in lbl
    assert ('BAR', 'TASK', 'FICOR77') not in lbl
    assert ('BAR', 'TASK', 'RESLOC') in lbl
    assert ('BAR', 'TASK', 'GEOMA') in lbl


def test_vicarlabel_setitem_after_key_new(lbl: Any) -> None:
    """Assigning to a new (name, after_name, after_value) inserts it after that block."""

    # Replace FOO after GEOMA with a second, then remove the first
    lbl['FOO+', 'TASK', 'GEOMA'] = 33
    del lbl['FOO', 'TASK', 'GEOMA']

    indx = lbl.arg('TASK', 'RESLOC')
    lbl['BAR', 'TASK', 'FICOR77'] = 99      # insertion
    assert lbl.arg(('BAR', 'TASK', 'FICOR77')) == indx
    assert ('BAR', 'TASK', 'FICOR77') in lbl
    assert list(lbl.names())[-8:] == ['TASK', 'FOO', 'BAR', 'TASK', 'BAR',
                                      'TASK', 'BAR', 'FOO']

    indx = len(lbl)
    lbl['NEW', 'TASK', 'GEOMA'] = 99
    assert lbl.arg(('NEW', 'TASK', 'GEOMA')) == indx
    assert ('NEW', 'TASK', 'GEOMA') in lbl
    assert list(lbl.names())[-9:] == ['TASK', 'FOO', 'BAR', 'TASK', 'BAR',
                                      'TASK', 'BAR', 'FOO', 'NEW']

    del lbl['FOO', 'TASK', 'GEOMA']
    assert list(lbl.names())[-3:] == ['TASK', 'BAR', 'NEW']


def test_vicarlabel_insert_and_delete() -> None:
    """insert() places a parameter at an index; del with "NAME+" removes by occurrence."""

    test = VicarLabel()
    ltest = len(test)
    test.insert('FOO=1', 1)
    test.append('FOO=2')
    test.append('FOO=3')
    assert len(test) == ltest + 3
    del test['FOO+', 1]
    assert len(test) == ltest + 1
    assert test[1] == 1


@pytest.mark.parametrize(('key', 'value'), [
    ('LBLSIZE', [1, 2]),
    ('LBLSIZE', 77.),
    (0, [1, 2]),
    (0, 77.),
])
def test_vicarlabel_lblsize_must_be_int(key: Any, value: Any) -> None:
    """LBLSIZE only accepts an integer."""

    test = VicarLabel()
    with pytest.raises(VicarError):
        test[key] = value


def test_vicarlabel_insert_before_lblsize() -> None:
    """Nothing can be inserted ahead of LBLSIZE."""

    test = VicarLabel()
    with pytest.raises(VicarError):
        test.insert('BAR=7', 0)

##########################################################################################
