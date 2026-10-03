##########################################################################################
# tests/conftest.py
# Shared fixtures for the vicar test suite
##########################################################################################

from pathlib import Path

import numpy as np
import pytest


_TEST_FILES = Path(__file__).resolve().parent.parent / 'test_files'

# The label of test_files/C2069302_GEOMA.DAT, including its EOL label, which begins at the
# second LBLSIZE.
_GEOMA_LABEL = (
    "LBLSIZE=1536            FORMAT='BYTE'  TYPE='TABULAR'  BUFSIZ=20480  "
    "DIM=3  EOL=1  RECSIZE=512  ORG='BSQ'    NS=512  NB=1  N1=512  N2=1  "
    "N3=1  N4=0  NBB=0    HOST='AXP-VMS'  INTFMT='LOW'  "
    "REALFMT='VAX'          NL=0            NLB=18  BHOST='AXP-VMS'  "
    "BINTFMT='LOW'  BREALFMT='VAX'  BLTYPE='IBIS'  "
    "PROPERTY='IBIS'                TYPE='TIEPOINT'  NR=552  NC=4  ORG='ROW'  "
    "FMT_DEFAULT='REAL'  GROUPS=('LINE','SAMP','C_POS_IMAGE','INPUT','POSITION',"
    "'C_POSITION','PIXEL','C_PIXEL','OUTPUT','C_POINT','C_ROOT')  GROUP_1=(3,1)  "
    "GROUP_2=(4,2)  GROUP_3=(3,4,1,2)  GROUP_4=(3,4)  GROUP_5=(1,2,3,4)  "
    "GROUP_6=(3,4,1,2)  GROUP_7=(1,2,3,4)  GROUP_8=(1,2,3,4)  GROUP_9=(1,2)  "
    "GROUP_10=(1,2,3,4)  GROUP_11=(3,4,1,2)  SEGMENT=16  BLOCKSIZE=512  "
    "COFFSET=(0,4,8,12)  PROPERTY='TIEPOINT'  NUMBER_OF_AREAS_HORIZONTAL=23  "
    "NUMBER_OF_AREAS_VERTICAL=22  TASK='TASK'  USER='SHOWALTER'  "
    "DAT_TIM='Sun Oct  2 05:05:17 2011'  "
    "LAB01='                     800     800 800 800 L 1                          SC'  "
    "LAB02='VGR-2   FDS 20693.02   PICNO 0215J2+001   SCET 79.192 01:19:58         C'  "
    "LAB03='WA CAMERA  EXP   15360.0 MSEC FILT 2(CLEAR )  LO GAIN  SCAN RATE  5:1  C'  "
    "LAB04='ERT 79.192 02:11:56   1/ 2 FULL    RES   VIDICON TEMP  -80.00 DEG C    C'  "
    "LAB05='IN/205140/14 OUT/xxxxxx/xx     J_RINGS     DSS #14   BIT SNR    6.273  C'  "
    "LAB06=' xxxxx A/xxxxxxxx B/xxxx C/xxxx D/xxxxxxxx ETLM/xxxxxxxxxxxxxxxxxxxxS AC'  "
    "LBLSIZE=1024            "
    "LAB07='NA OPCAL xx(015360.0*MSEC)PIXAVG 032/0 OPERATIONAL MODE 3(WAONLY)     AC'  "
    "LAB08='CAM ECAL CYCLE BEAM  RESET OPEN  CLOSE FLOOD AEXPM  FIL G1 SHUT MODE  AC'  "
    "LAB09='NA   NO   PREP  NO    YES   NO    NO    NO    NO    0 P  * NORMAL     AC'  "
    "LAB10='WA   NO   READ  YES   NO    NO    NO    NO    NO    2 P  7 NORMAL     AC'  "
    "LAB11='LSB_TRUNC=OFF  TLM_MODE=IM-2D COMPRESSION=OFF                          L'  "
    "NLABS=11    TASK='VGRFILLI'  USER='SHOWALTER'  DAT_TIM='Sun Oct  2 05:05:17 2011'  "
    "LIN_CNT=0  TASK='RESLOC'  USER='SHOWALTER'  DAT_TIM='Sun Oct  2 05:05:18 2011'    "
)


@pytest.fixture
def data_dir() -> Path:
    """The directory holding the VICAR files the tests read."""

    return _TEST_FILES


@pytest.fixture
def geoma_path() -> Path:
    """Path to C2069302_GEOMA.DAT, a tabular file with a binary header and EOL label."""

    return _TEST_FILES / 'C2069302_GEOMA.DAT'


@pytest.fixture
def geoma_label() -> str:
    """The full label text of C2069302_GEOMA.DAT."""

    return _GEOMA_LABEL


@pytest.fixture
def rng() -> np.random.Generator:
    """A seeded random number generator, so that failures can be reproduced."""

    return np.random.default_rng(20240228)

##########################################################################################
