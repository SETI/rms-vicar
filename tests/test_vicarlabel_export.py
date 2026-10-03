##########################################################################################
# tests/test_vicarlabel_export.py
# VicarLabel export(), as_string(), str(), and repr()
##########################################################################################

import pytest

from vicar.vicarlabel import VicarError, VicarLabel


def test_vicarlabel_export_resize(geoma_label: str) -> None:
    """With resize=True, the EOL label is folded into a single, larger label."""

    reference = VicarLabel(geoma_label)
    (label0, label1) = reference.export(resize=True)
    assert label1 == ''
    with pytest.raises(IndexError):
        reference[('LBLSIZE', 1)]
    assert len(label0) == reference['LBLSIZE']


def test_vicarlabel_export_no_resize(geoma_label: str) -> None:
    """With resize=False, each label keeps the LBLSIZE it was read with."""

    vic = VicarLabel(geoma_label)
    (label0, label1) = vic.export(resize=False)
    assert len(label0) == vic['LBLSIZE']
    assert len(label1) == vic[('LBLSIZE', 1)]


def test_vicarlabel_export_resize_fallback() -> None:
    """resize=False falls back to resizing when LBLSIZE is not a multiple of RECSIZE."""

    test = VicarLabel()
    test['RECSIZE'] = 100
    (label0, label1) = test.export(resize=False)
    assert len(label1) == 0         # resize switched to True

    test['RECSIZE'] = 200
    test['LBLSIZE'] = 200
    (label0, label1) = test.export(resize=False)
    assert len(label0) == 200
    assert len(label1) > 0          # resize preserved

    test['RECSIZE'] = 200
    test['LBLSIZE'] = 201
    (label0, label1) = test.export(resize=False)
    assert len(label1) == 0         # resize switched to True


def test_vicarlabel_export_after_deleting_labs(geoma_label: str) -> None:
    """Deleting parameters shrinks the label until the EOL label is unneeded."""

    vic = VicarLabel(geoma_label)
    for k in range(1, 11):
        del vic[f'LAB{k:02d}']

    (label0, label1) = vic.export(resize=False)
    assert len(label1) == 0
    assert len(label0) == vic['LBLSIZE']
    assert len(vic['LBLSIZE+']) == 1

    # Restoring them brings the EOL label back
    original = VicarLabel(geoma_label)
    for k in range(1, 11):
        vic[f'LAB{k:02d}'] = original[f'LAB{k:02d}']

    (label0, label1) = vic.export(resize=False)
    assert len(vic['LBLSIZE+']) == 2
    assert len(label1) == vic['LBLSIZE+'][1]
    assert len(label0) == vic['LBLSIZE']


def _small_label() -> VicarLabel:
    test = VicarLabel()
    test.append("LBLSIZE=100  NOTE='more stuff'")
    return test


def test_vicarlabel_as_string() -> None:
    """as_string() renders a slice of the label, with an optional separator."""

    test = _small_label()
    # The full string is not checked because HOST varies by platform.
    assert test.as_string(stop=17) == (
        "LBLSIZE=0             FORMAT='BYTE'  TYPE='IMAGE'  BUFSIZ=20480  "
        "DIM=3  EOL=0  RECSIZE=0  ORG='BSQ'  NL=0  NS=0  NB=0  N1=0  N2=0  "
        "N3=0  N4=0  NBB=0  NLB=0  ")
    assert test.as_string(start='BLTYPE') == (
        "BLTYPE=''  LBLSIZE=100           NOTE='more stuff'  ")
    assert test.as_string(start='BLTYPE', sep='xxx') == (
        "BLTYPE=''  xxxLBLSIZE=100           NOTE='more stuff'  ")
    assert test.as_string(start='BLTYPE', stop='NOTE', sep='xxx') == (
        "BLTYPE=''  xxxLBLSIZE=100           ")


def test_vicarlabel_str_and_repr() -> None:
    """str() is as_string(), and repr() evaluates back to an equal label."""

    test = _small_label()
    assert str(test) == test.as_string()
    assert eval(repr(test)) == test


def test_vicarlabel_delete_required() -> None:
    """The first occurrence of a required parameter cannot be deleted."""

    test = _small_label()
    reference = test.copy()
    test.append("ORG='ROWS'")

    for name in ('ORG', 'NLB', 'BLTYPE'):
        with pytest.raises(VicarError):
            del test[name]

    del test['ORG', 1]
    assert test == reference


##########################################################################################
