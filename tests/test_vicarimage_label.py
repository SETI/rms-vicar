##########################################################################################
# tests/test_vicarimage_label.py
# VicarImage label access, iteration, copy(), deepcopy(), and equality
##########################################################################################

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from vicar.vicarimage import VicarImage
from vicar.vicarlabel import VicarError


@pytest.fixture
def test(geoma_path: Path, tmp_path: Path, rng: np.random.Generator) -> Any:
    """GEOMA with an image and prefix added, after write_file() has merged its labels."""

    test = VicarImage(geoma_path)
    test.array = rng.standard_normal((2, 50, 72)).astype('f4')
    test.prefix = rng.integers(0, 256, (2, 50, 288), dtype='uint8')
    test.write_file(tmp_path / 'C2069302_GEOMA_with_image.DAT')
    return test


def test_vicarimage_indexing(test: Any) -> None:
    """Indexing, len(), str(), and repr() pass through to the label."""

    assert len(test) == len(test._label)
    assert 'RECSIZE' in test
    assert test['BUFSIZ'] == 20480
    assert test.get('BUFSIZ', 0) == 20480
    assert test.get('WHATEVER', 7) == 7
    assert str(test) == str(test._label)
    assert repr(test)[10:] == repr(test._label)[10:]
    assert len(test) == len(list(test))


@pytest.mark.parametrize('key', ['RECSIZE', ('RECSIZE', 0), 'arg'])
def test_vicarimage_immutable_parameters(test: Any, key: Any) -> None:
    """Parameters that describe the data layout cannot be changed or deleted."""

    if key == 'arg':
        key = test.arg('RECSIZE')

    with pytest.raises(VicarError):
        test[key] = 100
    with pytest.raises(VicarError):
        del test[key]


def test_vicarimage_second_occurrence_is_mutable(test: Any) -> None:
    """A later occurrence of an immutable parameter can be added and deleted."""

    test['RECSIZE+'] = 77
    with pytest.raises(VicarError):
        test['RECSIZE'] = 100
    with pytest.raises(VicarError):
        del test['RECSIZE']

    test['RECSIZE', 1] = 99
    del test['RECSIZE', 1]
    with pytest.raises(VicarError):
        test['RECSIZE'] = 100
    with pytest.raises(VicarError):
        del test['RECSIZE']


def test_vicarimage_iterators(test: Any) -> None:
    """names(), keys(), values(), items(), and args() pass through to the label."""

    assert list(test)[:3] == ['LBLSIZE', 'FORMAT', ('TYPE', 0)]

    assert list(test.names('TASK')) == ['TASK', 'TASK', 'TASK']
    assert list(test.names())[:3] == ['LBLSIZE', 'FORMAT', 'TYPE']

    assert list(test.keys('TASK')) == [('TASK', 0), ('TASK', 1), ('TASK', 2)]
    assert list(test.keys())[:3] == ['LBLSIZE', 'FORMAT', ('TYPE', 0)]

    assert list(test.values('TASK')) == ['TASK', 'VGRFILLI', 'RESLOC']
    assert list(test.values())[:3] == [2304, 'REAL', 'IMAGE']

    assert list(test.items('TASK', unique=False)) == [('TASK', 'TASK'),
                                                      ('TASK', 'VGRFILLI'),
                                                      ('TASK', 'RESLOC')]
    assert list(test.items('TASK', unique=True)) == [(('TASK', 0), 'TASK'),
                                                     (('TASK', 1), 'VGRFILLI'),
                                                     (('TASK', 2), 'RESLOC')]
    assert list(test.items(unique=False))[:3] == [('LBLSIZE', 2304), ('FORMAT', 'REAL'),
                                                  ('TYPE', 'IMAGE')]
    assert list(test.items(unique=True))[:3] == [('LBLSIZE', 2304), ('FORMAT', 'REAL'),
                                                 (('TYPE', 0), 'IMAGE')]

    groups = [('GROUP_1', [3, 1]),
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
    assert list(test.items(r'GROUP_\d+')) == groups
    assert list(test.values(r'GROUP_\d+')) == [g[1] for g in groups]
    assert list(test.args(r'GROUP_\d+')) == list(range(31, 42))
    assert list(test.args()) == list(range(70))


def test_vicarimage_delete_and_append(test: Any) -> None:
    """A deleted parameter can be appended again with "NAME+"."""

    len0 = len(test)
    last_dat_time = test[('DAT_TIM', -1)]
    del test[('DAT_TIM', -1)]
    assert len(test) == len0 - 1
    test['DAT_TIM+'] = last_dat_time
    assert len(test) == len0


def test_vicarimage_copy(data_dir: Path) -> None:
    """copy() shares the arrays; changing one copy's array leaves the other's alone."""

    vim = VicarImage(data_dir / 'C2069302_GEOMED.IMG')
    vim2 = vim.copy()
    assert vim == vim2
    assert vim.array is vim2.array
    assert vim is not vim2

    vim2.array = None
    assert vim2.array is None
    assert vim.array is not None

    vim3 = VicarImage(vim2.label)
    vim2.prefix = None
    vim2.binheader = None
    assert vim2 == vim3


def test_vicarimage_deepcopy(data_dir: Path) -> None:
    """deepcopy() copies the arrays too."""

    vim = VicarImage(data_dir / 'C2069302_GEOMED.IMG')
    vim2 = vim.deepcopy()
    assert vim is not vim2
    assert vim.array is not vim2.array
    assert np.all(vim.array == vim2.array)

    assert vim != set()

##########################################################################################
