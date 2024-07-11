##########################################################################################
# tests/test_vicarlabel.py
##########################################################################################

import os
import pathlib
import shutil
import sys
import unittest
from vicar.vicarlabel import VicarLabel, VicarError, _REQUIRED
from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR


class Test_VicarLabel(unittest.TestCase):

    def test_VicarLabelGO(self):

        vicar_dir = pathlib.Path(sys.modules['vicar'].__file__)
        test_dir = vicar_dir.parent.parent / 'test_files'

        text = (
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

        def test_vic(source):

            vic = VicarLabel(source)
            self.assertEqual(vic['LBLSIZE'], 1536)
            self.assertEqual(vic[('LBLSIZE',0)], 1536)
            self.assertEqual(vic[('LBLSIZE',1)], 1024)
            self.assertEqual(vic[('LBLSIZE',-1)], 1024)
            self.assertEqual(vic[('LBLSIZE',-2)], 1536)
            self.assertEqual(vic['LBLSIZE+'], [1536,1024])
            self.assertRaises(KeyError, vic.__getitem__, 'FOO')
            self.assertRaises(KeyError, vic.__getitem__, 'FOO+')
            self.assertRaises(TypeError, vic.__getitem__, 3.14159)
            self.assertRaises(IndexError, vic.__getitem__, ('LBLSIZE',2))
            self.assertRaises(TypeError, vic.__getitem__, set())

            self.assertIn('LBLSIZE', vic)
            self.assertIn(('LBLSIZE',0), vic)
            self.assertIn(('LBLSIZE',1), vic)
            self.assertNotIn(('LBLSIZE',2), vic)
            self.assertIn(('LBLSIZE',-1), vic)
            self.assertNotIn(('LBLSIZE',-3), vic)
            self.assertNotIn('FOO', vic)

            self.assertEqual(vic[0], 1536)
            self.assertEqual(vic[-2], 'SHOWALTER')
            self.assertRaises(IndexError, vic.__getitem__, 999)

            self.assertEqual(vic.get('LBLSIZE', -1), 1536)
            self.assertEqual(vic.get(('LBLSIZE',0), -1), 1536)
            self.assertEqual(vic.get(('LBLSIZE',1), -1), 1024)
            self.assertEqual(vic.get(('LBLSIZE',2), -1), -1)

            self.assertEqual(len(vic), 71)

            self.assertEqual(vic.arg('LBLSIZE'), 0)
            self.assertEqual(vic.arg('DIM'), 4)
            self.assertEqual(vic.arg(('LBLSIZE',1)), 57)

            self.assertEqual(vic.arg(0), 0)
            self.assertEqual(vic.arg(4), 4)
            self.assertEqual(vic.arg(-1), 70)
            self.assertEqual(vic.arg(-71), 0)
            self.assertRaises(IndexError, vic.arg, 71)
            self.assertRaises(IndexError, vic.arg, -72)
            self.assertRaises(IndexError, vic.arg, ('LBLSIZE',2))
            self.assertRaises(KeyError, vic.arg, ('FOO',0))

            # Iterators

            self.assertEqual(list(vic)[:3], [('LBLSIZE',0), 'FORMAT', ('TYPE',0)])

            self.assertEqual(list(vic.names('TASK')), ['TASK', 'TASK', 'TASK'])
            self.assertEqual(list(vic.names())[:3], ['LBLSIZE', 'FORMAT', 'TYPE'])

            self.assertEqual(list(vic.keys('TASK')), [('TASK',0), ('TASK',1), ('TASK',2)])
            self.assertEqual(list(vic.keys())[:3], [('LBLSIZE',0), 'FORMAT', ('TYPE',0)])

            self.assertEqual(list(vic.values('TASK')), ['TASK', 'VGRFILLI', 'RESLOC'])
            self.assertEqual(list(vic.values())[:3], [1536, 'BYTE', 'TABULAR'])

            self.assertEqual(list(vic.items('TASK', unique=False)),
                             [('TASK','TASK'), ('TASK','VGRFILLI'), ('TASK','RESLOC')])
            self.assertEqual(list(vic.items('TASK', unique=True)),
                             [(('TASK',0), 'TASK'), (('TASK',1), 'VGRFILLI'),
                              (('TASK',2), 'RESLOC')])
            self.assertEqual(list(vic.items(unique=False))[:3],
                             [('LBLSIZE', 1536), ('FORMAT', 'BYTE'), ('TYPE', 'TABULAR')])
            self.assertEqual(list(vic.items(unique=True))[:3],
                             [(('LBLSIZE',0), 1536), ('FORMAT', 'BYTE'),
                              (('TYPE',0), 'TABULAR')])

            self.assertEqual(list(vic.items(r'GROUP_\d+')), [('GROUP_1', [3, 1]),
                                                             ('GROUP_2', [4, 2]),
                                                             ('GROUP_3', [3, 4, 1, 2]),
                                                             ('GROUP_4', [3, 4]),
                                                             ('GROUP_5', [1, 2, 3, 4]),
                                                             ('GROUP_6', [3, 4, 1, 2]),
                                                             ('GROUP_7', [1, 2, 3, 4]),
                                                             ('GROUP_8', [1, 2, 3, 4]),
                                                             ('GROUP_9', [1, 2]),
                                                             ('GROUP_10', [1, 2, 3, 4]),
                                                             ('GROUP_11', [3, 4, 1, 2])])
            self.assertEqual(list(vic.values(r'GROUP_\d+')), [[3, 1],
                                                              [4, 2],
                                                              [3, 4, 1, 2],
                                                              [3, 4],
                                                              [1, 2, 3, 4],
                                                              [3, 4, 1, 2],
                                                              [1, 2, 3, 4],
                                                              [1, 2, 3, 4],
                                                              [1, 2],
                                                              [1, 2, 3, 4],
                                                              [3, 4, 1, 2]])

            self.assertEqual(list(vic.args(r'GROUP_\d+')), list(range(31,42)))
            self.assertEqual(list(vic.args()), list(range(71)))

        # Alternative sources: text string, file, list of tuples
        test_vic(text)
        test_vic(test_dir / 'C2069302_GEOMA.DAT')
        test_vic(str(test_dir / 'C2069302_GEOMA.DAT'))

        with open(test_dir / 'C2069302_GEOMA.DAT', 'rb') as f:
            test_vic(f)
            self.assertFalse(f.closed)
        self.assertTrue(f.closed)

        params = _LABEL_GRAMMAR.parse_string(text).as_list()
        test_vic(params)

        # __eq__
        reference = VicarLabel(text)
        self.assertEqual(reference, VicarLabel(test_dir / 'C2069302_GEOMA.DAT'))
        self.assertEqual(reference, VicarLabel(str(test_dir / 'C2069302_GEOMA.DAT')))
        self.assertEqual(reference, VicarLabel.from_file(test_dir / 'C2069302_GEOMA.DAT'))
        self.assertEqual(reference, VicarLabel(params))
        self.assertNotEqual(reference, set())

        # append
        parts = text.partition('LBLSIZE=1024')
        vic2 = VicarLabel(parts[0])
        vic2.append(parts[1] + parts[2])
        self.assertEqual(reference, vic2)

        vic3 = vic2.copy()
        vic2.append('PI=3.14159')
        vic3.append([('PI', 3.14159)])
        self.assertEqual(vic3, vic3)

        # skip over LBLSIZE and it will be filled in
        params = _LABEL_GRAMMAR.parse_string(parts[0]).as_list()
        missing_lblsize = VicarLabel(params[1:])
        self.assertEqual(missing_lblsize.names()[0], 'LBLSIZE')
        self.assertEqual(missing_lblsize['LBLSIZE'], 0)
        missing_lblsize[0] = (1536, 12)
        missing_lblsize.append(parts[1] + parts[2])
        self.assertEqual(reference, missing_lblsize)

        # export
        (label0, label1) = reference.export(resize=True)
        self.assertEqual(label1, '')
        self.assertRaises(IndexError, reference.__getitem__, ('LBLSIZE',1))
        self.assertEqual(len(label0), reference['LBLSIZE'])

        vic = VicarLabel(text)  # reinitialize
        (label0, label1) = vic.export(resize=False)
        self.assertEqual(len(label0), vic['LBLSIZE'])
        self.assertEqual(len(label1), vic[('LBLSIZE',1)])

        test = VicarLabel()
        test['RECSIZE'] = 100
        (label0, label1) = test.export(resize=False)
        self.assertEqual(len(label1), 0)    # resize switched to True

        test['RECSIZE'] = 200
        test['LBLSIZE'] = 200
        (label0, label1) = test.export(resize=False)
        self.assertEqual(len(label0), 200)
        self.assertGreater(len(label1), 0)  # resize preserved

        test['RECSIZE'] = 200
        test['LBLSIZE'] = 201
        (label0, label1) = test.export(resize=False)
        self.assertEqual(len(label1), 0)    # resize switched to True

        # as_string, __str__, __repr__
        test = VicarLabel()
        test.append("LBLSIZE=100  NOTE='more stuff'")
        # Fails on platforms other than Mac
#     self.assertEqual(test.as_string(),
#                      "LBLSIZE=0             FORMAT='BYTE'  TYPE='IMAGE'  BUFSIZ=20480  "
#                      "DIM=3  EOL=0  RECSIZE=0  ORG='BSQ'  NL=0  NS=0  NB=0  N1=0  N2=0  "
#                      "N3=0  N4=0  NBB=0  NLB=0  HOST='MAC-OSX'  INTFMT='LOW'  "
#                      "REALFMT='RIEEE'  BHOST='MAC-OSX'  BINTFMT='LOW'  BREALFMT='RIEEE'  "
#                      "BLTYPE=''  LBLSIZE=100           NOTE='more stuff'  ")
        self.assertEqual(test.as_string(stop=17),
                         "LBLSIZE=0             FORMAT='BYTE'  TYPE='IMAGE'  BUFSIZ=20480  "
                         "DIM=3  EOL=0  RECSIZE=0  ORG='BSQ'  NL=0  NS=0  NB=0  N1=0  N2=0  "
                         "N3=0  N4=0  NBB=0  NLB=0  ")
        self.assertEqual(test.as_string(start='BLTYPE'),
                         "BLTYPE=''  LBLSIZE=100           NOTE='more stuff'  ")
        self.assertEqual(test.as_string(start='BLTYPE', sep='xxx'),
                         "BLTYPE=''  xxxLBLSIZE=100           NOTE='more stuff'  ")
        self.assertEqual(test.as_string(start='BLTYPE', stop='NOTE', sep='xxx'),
                         "BLTYPE=''  xxxLBLSIZE=100           ")

        self.assertEqual(str(test), test.as_string())
        test2 = eval(repr(test))
        self.assertEqual(test, test2)

        # del of required
        test.append("ORG='ROWS'")
        with self.assertRaises(VicarError):
            del test['ORG']

        with self.assertRaises(VicarError):
            del test['NLB']

        with self.assertRaises(VicarError):
            del test['BLTYPE']

        del test['ORG',1]
        self.assertEqual(test2, test)

        # del
        vic = VicarLabel(text)  # reinitialize
        for k in range(1,11):
            del vic['LAB' + ('%02d' % k)]

        (label0, label1) = vic.export(resize=False)
        self.assertEqual(len(label1), 0)
        self.assertEqual(len(label0), vic['LBLSIZE'])
        self.assertEqual(len(vic['LBLSIZE+']), 1)

        # Restore LABxx
        vic2 = VicarLabel(text)
        for k in range(1,11):
            vic['LAB' + ('%02d' % k)] = vic2['LAB' + ('%02d' % k)]

        (label0, label1) = vic.export(resize=False)
        self.assertEqual(len(vic['LBLSIZE+']), 2)
        self.assertEqual(len(label1), vic['LBLSIZE+'][1])
        self.assertEqual(len(label0), vic['LBLSIZE'])

        # write_label
        dest = test_dir / 'C2069302_GEOMA_new_label.DAT'
        shutil.copy(test_dir / 'C2069302_GEOMA.DAT', dest)
        vic = VicarLabel(dest)
        for k in range(1,11):
            del vic['LAB' + ('%02d' % k)]
        vic.write_label(dest)

        altvic = VicarLabel(dest)
        self.assertEqual(vic, altvic)
        self.assertEqual(len(vic['LBLSIZE+']), 1)
        self.assertEqual(os.path.getsize(dest), vic['LBLSIZE'] + vic['RECSIZE'] * vic['NLB'])
        self.assertEqual(altvic.filepath, dest)

        vic2 = VicarLabel(text)
        for k in range(1,11):
            vic['LAB' + ('%02d' % k)] = vic2['LAB' + ('%02d' % k)]

        vic.write_label()

        altvic = VicarLabel(dest)
        self.assertEqual(vic, altvic)
        self.assertEqual(len(vic['LBLSIZE+']), 2)
        self.assertEqual(os.path.getsize(dest),
                         vic['LBLSIZE'] + vic['RECSIZE'] * vic['NLB'] + vic[('LBLSIZE',1)])

        altvic.filepath = None
        self.assertRaises(ValueError, altvic.write_label)

        altvic.filepath = str(dest)
        self.assertIsInstance(altvic.filepath, pathlib.Path)
        self.assertEqual(altvic.filepath, dest)

        os.remove(dest)     # delete extra file

        # Empty label
        empty = VicarLabel()
        self.assertEqual(len(empty), len(_REQUIRED))

        # Single tuple
        almost_empty = VicarLabel(('SEVEN', 7.0))
        self.assertEqual(len(almost_empty), len(_REQUIRED) + 1)
        almost_empty2 = VicarLabel({'SEVEN': (7.,)})
        self.assertEqual(almost_empty, almost_empty2)
        almost_empty2 = VicarLabel({'SEVEN': (7.,'')})
        self.assertEqual(almost_empty, almost_empty2)

        # Dict
        almost_empty2 = VicarLabel({'SEVEN': 7.})
        self.assertEqual(almost_empty, almost_empty2)
        almost_empty2 = VicarLabel({'SEVEN': (7.,)})
        self.assertEqual(almost_empty, almost_empty2)

        # Invalid inputs
        self.assertRaises(VicarError, VicarLabel,
                          "FORMAT='BYTE'  SEVEN=7.0  LBLSIZE=100  MORE=xyz")
        self.assertRaises(TypeError, VicarLabel, set([1,2,3]))
        self.assertRaises(TypeError, VicarLabel, [('LBLSIZE',100), set()])
        self.assertRaises(TypeError, VicarLabel, [('LBLSIZE',100), ('RECSIZE',)])
        self.assertRaises(TypeError, VicarLabel, [('LBLSIZE',100), 'RECSIZE'])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('TWO',2.,'',4,5,6,7)])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('TWO',2.,3,4,5,6)])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('TWO',2.,3,'')])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), (1,2.)])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('TWo',2.)])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('CR','\n')])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('LIST1',[])])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('LIST2',[1,2.])])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('SET',set())])
        self.assertRaises(VicarError, VicarLabel, [('LBLSIZE',100), ('SET',[set()])])
        self.assertRaises(VicarError, VicarLabel, [('A23456789012345678901234567890123',7)])
        test = VicarLabel([('A2345678901234567890123456789012',7)])
        test = VicarLabel([('LBLSIZE',100), ('TWo',2.), ('CR','\n'), ('LIST1',[]),
                           ('LIST2',[1,2.]), ('A23456789012345678901234567890123',7)],
                          strict=False)
        self.assertRaises(VicarError, VicarLabel,
                          [('LBLSIZE',100), ('SET',[1,2,set()])], strict=False)

        # Invalid formats
        self.assertRaises(TypeError, VicarLabel, [('ABC', 4, '%.4f')])
        self.assertRaises(TypeError, VicarLabel, [('ABC', 4, '%.4g')])
        self.assertRaises(TypeError, VicarLabel, [('ABC', 4, '%.4e')])
        self.assertRaises(TypeError, VicarLabel, [('ABC', 4., '%4d')])
        self.assertRaises(TypeError, VicarLabel, [('ABC', 4., '%4i')])
        self.assertRaises(TypeError, VicarLabel, [('ABC', 'abc', '%4i')])
        self.assertRaises(TypeError, VicarLabel, [('ABC', 'abc', '%s')])

        self.assertRaises(TypeError, VicarLabel, [('ABC', [(4, '%.4f')])])
        self.assertRaises(TypeError, VicarLabel, [('ABC', [(4, '%.4g')])])
        self.assertRaises(TypeError, VicarLabel, [('ABC', [(4, '%.4e')])])
        self.assertRaises(TypeError, VicarLabel, [('ABC', [(4., '%4d')])])
        self.assertRaises(TypeError, VicarLabel, [('ABC', [(4., '%4i')])])
        self.assertRaises(TypeError, VicarLabel, [('ABC', [('abc', '%4i')])])
        self.assertRaises(TypeError, VicarLabel, [('ABC', [('abc', '%s')])])
        self.assertRaises(VicarError, VicarLabel, [('ABC', [(7, '%02d', 1, 2, 3)])])

        # Moving LBLSIZE to front
        vic = VicarLabel("FORMAT='BYTE'  SEVEN=7.0  LBLSIZE=100  MORE='LESS'")
        self.assertEqual(vic.items()[0], ('LBLSIZE', 100))

        # __setitem__, validation
        self.assertRaises(VicarError, vic.__setitem__, '_INVALID_NAME', 1)
        self.assertRaises(VicarError, vic.__setitem__, 'TUPLE', [])     # no empty lists
        self.assertRaises(VicarError, vic.__setitem__, 'SET', set())
        self.assertRaises(VicarError, vic.__setitem__, 'LIST', [1,2.])
        self.assertRaises(VicarError, vic.__setitem__, 'LIST', [1.,'TWO'])
        self.assertRaises(VicarError, vic.__setitem__, 'LIST', ['ONE', set()])
        self.assertRaises(VicarError, vic.__setitem__, 'LIST', [set(), 2])

        self.assertRaises(TypeError, vic.__setitem__, set(), 7)
        self.assertRaises(TypeError, vic.__setitem__, 3.14, 'pi')
        self.assertRaises(VicarError, vic.__setitem__, 0, set())

        self.assertRaises(VicarError, vic.__setitem__, 'ORG', 'whatever')
        self.assertRaises(VicarError, vic.__setitem__, 'NL', 'whatever')
        self.assertRaises(VicarError, vic.__setitem__, 'NL', -1)

        # __setitem__, value_str
        vic['A'] = 1
        self.assertEqual(vic.value_str('A'), '1')
        vic['A'] = (1, '%+03d')
        self.assertEqual(vic.value_str('A'), '+01')
        vic['A'] = 3
        self.assertEqual(vic.value_str('A'), '+03')         # format preserved
        vic['A'] = (1, '%+03d', 3)
        self.assertEqual(vic.value_str('A'), '+01   ')
        vic['A'] = 4
        self.assertEqual(vic.value_str('A'), '+04   ')
        vic['A'] = 4.
        self.assertEqual(vic.value_str('A'), '4.   ')       # format replaced
        vic['A'] = 4
        self.assertEqual(vic.value_str('A'), '4   ')
        vic['A'] = (1, '%+03d', 3, 0)
        self.assertEqual(vic.value_str('A'), '   +01')
        vic['A'] = 4
        self.assertEqual(vic.value_str('A'), '   +04')
        vic['A'] = (1, 3, 0)
        self.assertEqual(vic.value_str('A'), '   1')
        vic['A'] = 4
        self.assertEqual(vic.value_str('A'), '   4')
        vic['A'] = (1, 3)
        self.assertEqual(vic.value_str('A'), '1   ')
        vic['A'] = 4
        self.assertEqual(vic.value_str('A'), '4   ')

        vic['B'] = 1.234
        self.assertEqual(vic.value_str('B'), '1.234')
        vic['B'] = (1.234, '%#+.4f')
        self.assertEqual(vic.value_str('B'), '+1.2340')
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '+1.2346')     # format preserved
        vic['B'] = (1.234, '%#.0f')
        self.assertEqual(vic.value_str('B'), '1.')
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '1.')
        vic['B'] = (1.234, '%#+.4f', 3)
        self.assertEqual(vic.value_str('B'), '+1.2340   ')
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '+1.2346   ')
        vic['B'] = 1
        self.assertEqual(vic.value_str('B'), '1   ')        # format replaced
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '1.23456   ')  # format replaced
        vic['B'] = (1.234, '%#+.4f', 3, 0)
        self.assertEqual(vic.value_str('B'), '   +1.2340')
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '   +1.2346')
        vic['B'] = (1.234, 3, 0)
        self.assertEqual(vic.value_str('B'), '   1.234')
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '   1.23456')
        vic['B'] = (1.234, 3)
        self.assertEqual(vic.value_str('B'), '1.234   ')
        vic['B'] = 1.23456
        self.assertEqual(vic.value_str('B'), '1.23456   ')

        vic['C'] = 1.234999993535
        self.assertEqual(vic.value_str('C'), '1.235')
        vic['C'] = -1.23500000123
        self.assertEqual(vic.value_str('C'), '-1.235')
        vic['C'] = 1.000001999999
        self.assertEqual(vic.value_str('C'), '1.')
        vic['C'] = -1.9999900000
        self.assertEqual(vic.value_str('C'), '-2.')
        vic['C'] = 9.9999900000
        self.assertEqual(vic.value_str('C'), '10.')
        vic['C'] = 1.899999050000044
        self.assertEqual(vic.value_str('C'), '1.9')
        vic['C'] = -1.02999998434
        self.assertEqual(vic.value_str('C'), '-1.03')

        vic['D'] = -1.234999993535e-12
        self.assertEqual(vic.value_str('D'), '-1.235E-12')
        vic['D'] = 1.23500000123e-12
        self.assertEqual(vic.value_str('D'), '1.235E-12')
        vic['D'] = -1.000001999999e-12
        self.assertEqual(vic.value_str('D'), '-1.E-12')
        vic['D'] = 1.9999900000e-12
        self.assertEqual(vic.value_str('D'), '2.E-12')
        vic['D'] = -9.9999900000e-12
        self.assertEqual(vic.value_str('D'), '-1.E-11')
        vic['D'] = 1.899999050000044e-12
        self.assertEqual(vic.value_str('D'), '1.9E-12')
        vic['D'] = -1.02999998434e-12
        self.assertEqual(vic.value_str('D'), '-1.03E-12')

        vic['E'] = 7.
        self.assertEqual(vic.value_str('E'), '7.')

        vic['F'] = [1.234, -1.234999993535e-12]
        self.assertEqual(vic.value_str('F'), '(1.234,-1.235E-12)')
        vic['F'] = [(1.234, '%#+.4f'), -1.23500000123, -1.000001999999e-12]
        self.assertEqual(vic.value_str('F'), '(+1.2340,-1.235,-1.E-12)')
        vic['F'] = [(1.234, 1, 0), (7., 1), -1.02999998434e-12]
        self.assertEqual(vic.value_str('F'), '( 1.234,7. ,-1.03E-12)')
        vic['F'] = ([(1.234, 1, 0), (7., 1), -1.02999998434e-12], 2, 3)
        self.assertEqual(vic.value_str('F'), '  ( 1.234,7. ,-1.03E-12)   ')

        vic['G'] = 'xyz'
        self.assertEqual(vic.value_str('G'), "'xyz'")
        vic['G'] = ('xyz', 3)
        self.assertEqual(vic.value_str('G'),"'xyz'   ")
        vic['G'] = 'abc'
        self.assertEqual(vic.value_str('G'),"'abc'   ")
        vic['G'] = ('abc', 3, 1)
        self.assertEqual(vic.value_str('G'),"   'abc' ")
        vic['G'] = 'xyz'
        self.assertEqual(vic.value_str('G'),"   'xyz' ")

        vic['H'] = [1,2,3]
        self.assertEqual(vic.value_str('H'), "(1,2,3)")
        vic['H'] = ([1,2,3], 2, 1)
        self.assertEqual(vic.value_str('H'), "  (1,2,3) ")
        vic['H'] = [4,5,6,7]
        self.assertEqual(vic.value_str('H'), "  (4,5,6,7) ")
        vic['H'] = [(1,1,1), (2,2,2), (3,3,3)]
        self.assertEqual(vic.value_str('H'), "( 1 ,  2  ,   3   )")
        vic['H'] = [4,5,6,7]
        self.assertEqual(vic.value_str('H'), "(4,5,6,7)")
        vic['H'] = ([(1,1,1), (2,2,2), (3,3,3)], 2, 1)
        self.assertEqual(vic.value_str('H'), "  ( 1 ,  2  ,   3   ) ")
        vic['H'] = [4,5,6,7]
        self.assertEqual(vic.value_str('H'), "  (4,5,6,7) ")

        vic['ORG+'] = 'not BSQ or BIL or BIP'   # not a VicarError
        self.assertEqual(vic.value_str(('ORG',-1)), "'not BSQ or BIL or BIP'")

        # copy
        vic2 = vic.copy()
        self.assertEqual(vic, vic2)
        vic2['E'] = 9.
        self.assertEqual(vic['E'], 7.)
        vic2['NEW_ITEM'] = 'This is a new item'
        self.assertEqual(len(vic), len(vic2) - 1)

        # reorder
        vic.reorder('', 'A', 'B', 'C', 'F')
        self.assertEqual(vic.names()[:6], ['LBLSIZE', 'A', 'B', 'C', 'F', 'FORMAT'])
        self.assertRaises(KeyError, vic.reorder, 'A', 'UNK', 'C', 'F')
        self.assertRaises(ValueError, vic.reorder, 'A', 'F', 'C', 'F')

        vic.reorder('FORMAT', 'F', 'G')
        self.assertEqual(vic.names()[:7], ['LBLSIZE', 'A', 'B', 'C', 'FORMAT', 'F', 'G'])

        # _set_n321, _set_nbls, _n123_from_nbls, _nbls_from_n123
        vic['ORG'] = 'BSQ'
        vic._set_n321(300, 200, 100)
        self.assertEqual((vic['N3'], vic['N2'], vic['N1']), (300, 200, 100))
        self.assertEqual((vic['NB'], vic['NL'], vic['NS']), (300, 200, 100))
        vic._set_nbls(101, 201, 301)
        self.assertEqual((vic['NB'], vic['NL'], vic['NS']), (101, 201, 301))
        self.assertEqual((vic['N3'], vic['N2'], vic['N1']), (101, 201, 301))

        vic['ORG'] = 'BIL'
        vic._set_n321(300, 200, 100)
        self.assertEqual((vic['N3'], vic['N2'], vic['N1']), (300, 200, 100))
        self.assertEqual((vic['NL'], vic['NB'], vic['NS']), (300, 200, 100))
        vic._set_nbls(101, 201, 301)
        self.assertEqual((vic['NB'], vic['NL'], vic['NS']), (101, 201, 301))
        self.assertEqual((vic['N2'], vic['N3'], vic['N1']), (101, 201, 301))

        vic['ORG'] = 'BIP'
        vic._set_n321(300, 200, 100)
        self.assertEqual((vic['N3'], vic['N2'], vic['N1']), (300, 200, 100))
        self.assertEqual((vic['NL'], vic['NS'], vic['NB']), (300, 200, 100))
        vic._set_nbls(101, 201, 301)
        self.assertEqual((vic['NB'], vic['NL'], vic['NS']), (101, 201, 301))
        self.assertEqual((vic['N1'], vic['N3'], vic['N2']), (101, 201, 301))

        # Reading image file C0532836239R.IMG

        filepath = test_dir / 'C0532836239R.IMG'

        vic = VicarLabel(filepath)

        self.assertEqual(vic.filepath, filepath)
        self.assertEqual(vic['NL'], 800)
        self.assertEqual(vic['TRUTH_WINDOW'], [801,801,96,96])
        self.assertEqual(vic['COMPRESSION_RATIO'], 9.64155)
        self.assertEqual(vic['SOLRANGE'], 7.43341E+08)
        self.assertEqual(vic['TARGET'], 'EUROPA')

        test = VicarLabel.read_label(filepath)
        self.assertEqual(vic, VicarLabel(test))

        f = filepath.open('rb')
        test2 = VicarLabel.read_label(f)
        self.assertEqual(test2, test)
        f.close()

        (test3, extra) = VicarLabel.read_label(filepath, _extra=True)
        self.assertEqual(test3, test)
        size = vic['LBLSIZE'] + (vic['NL'] + vic['NLB']) * vic['RECSIZE']
        self.assertEqual(size + len(extra), os.path.getsize(filepath))
        self.assertTrue(all([c == 0 for c in extra]))

        # New __setitem__ features 2/28/24
        lbl = VicarLabel()
        lbl['NEW1', 0] = 1
        lbl['NEW2+', 0] = 2
        lbl['NEW3', 0] = 3
        lbl['NEW4+', 0] = 4
        lbl['NEW5'] = 5
        lbl['NEW5', 1] = 6
        self.assertEqual(lbl['NEW1'], 1)
        self.assertEqual(lbl['NEW2'], 2)
        self.assertEqual(lbl['NEW3'], 3)
        self.assertEqual(lbl['NEW4'], 4)
        self.assertEqual(lbl['NEW5+'], [5,6])

        self.assertRaises(KeyError, lbl.__setitem__, ('NEW6', 1), 7)
        self.assertRaises(KeyError, lbl.__setitem__, ('NEW6',-2), 8)

        # New features 2/29/24
        # append() using a dictionary
        lbl = VicarLabel()
        lbl.append({'A':1, 'B':'TWO', 'C':(3, '%03d', 1, 1)})
        self.assertEqual(lbl['A'], 1)
        self.assertEqual(lbl['B'], 'TWO')
        self.assertEqual(lbl['C'], 3)
        self.assertEqual(lbl._formats[-1], ('%03d', 0, 1, 1, []))

        # arg() with a value
        lbl = VicarLabel()
        lbl.append({'TASK':'FICOR77', 'FOO':1})
        lbl.append({'TASK':'RESLOC', 'BAR':2})
        lbl.append({'TASK':'GEOMA', 'FOO':3, 'BAR':4})

        self.assertEqual(lbl.arg('TASK', 'GEOMA'), len(lbl) - 3)
        self.assertEqual(lbl.arg('TASK', 'FICOR77'), len(lbl) - 7)
        self.assertEqual(lbl.arg(len(lbl) - 3, 'GEOMA'), len(lbl) - 3)
        self.assertRaises(ValueError, lbl.arg, 'TASK', 'whatever')
        self.assertRaises(ValueError, lbl.arg, len(lbl) - 3, 'RESLOC')

        # arg() with a new key
        self.assertEqual(lbl.arg(('FOO', 'TASK', 'FICOR77'), 1), len(lbl) - 6)
        self.assertEqual(lbl.arg(('BAR', 'TASK', 'RESLOC'), 2), len(lbl) - 4)
        self.assertEqual(lbl.arg(('FOO', 'TASK', 'GEOMA'), 3), len(lbl) - 2)
        self.assertEqual(lbl.arg(('BAR', 'TASK', 'GEOMA'), 4), len(lbl) - 1)

        self.assertEqual(lbl.arg(('FOO', 'TASK', 'FICOR77')), len(lbl) - 6)
        self.assertEqual(lbl.arg(('BAR', 'TASK', 'RESLOC')), len(lbl) - 4)
        self.assertEqual(lbl.arg(('FOO', 'TASK', 'GEOMA')), len(lbl) - 2)
        self.assertEqual(lbl.arg(('BAR', 'TASK', 'GEOMA')), len(lbl) - 1)

        self.assertRaises(ValueError, lbl.arg, ('FOO', 'TASK', 'GEOMA'), 99)
        self.assertRaises(KeyError, lbl.arg, ('FOO', 'TASK', 'RESLOC'))

        # __getitem__() with a new key
        self.assertEqual(lbl['FOO', 'TASK'], 1)
        self.assertEqual(lbl['FOO', 'TASK', 'FICOR77'], 1)
        self.assertEqual(lbl['BAR', 'TASK', 'RESLOC'], 2)
        self.assertEqual(lbl['FOO', 'TASK', 'GEOMA'], 3)
        self.assertEqual(lbl['BAR', 'TASK', 'GEOMA'], 4)

        self.assertRaises(KeyError, lbl.__getitem__, ('BAR', 'TASK'))
        self.assertRaises(KeyError, lbl.__getitem__, ('BAR', 'TASK', 'FICOR77'))
        self.assertRaises(KeyError, lbl.__getitem__, ('FOO', 'TASK', 'RESLOC'))

        self.assertRaises(KeyError, lbl.__getitem__, ('FOO', 'TASKX'))
        self.assertRaises(KeyError, lbl.__getitem__, ('FOO', 'TASKX', 'whatever'))
        self.assertRaises(ValueError, lbl.__getitem__, ('FOO', 'TASK', 'RESSAR77'))

        # get() with a new key
        test = VicarLabel()
        self.assertEqual(test.get('FOO', 7), 7)
        self.assertEqual(test.get('FOO+', 7), [7])
        self.assertEqual(test.get(set(), 7), 7)

        # __setitem__() with a new key, existing
        lbl['FOO', 'TASK', 'FICOR77'] = 77
        self.assertEqual(lbl['FOO', 'TASK', 'FICOR77'], 77)
        self.assertEqual(lbl[len(lbl) - 6], 77)

        lbl['FOO', 'TASK', 'GEOMA'] = 88
        self.assertEqual(lbl['FOO', 'TASK', 'GEOMA'], 88)
        self.assertEqual(lbl[len(lbl) - 2], 88)

        lbl['FOO+', 'TASK', 'GEOMA'] = 33
        self.assertEqual(lbl['FOO+', 'TASK', 'GEOMA'], [88,33])
        del lbl['FOO', 'TASK', 'GEOMA']
        self.assertEqual(lbl['FOO+', 'TASK', 'GEOMA'], [33])

        # __contains__() with an integer key
        self.assertTrue(-len(lbl) in lbl)
        self.assertTrue(len(lbl) - 1 in lbl)
        self.assertFalse(-len(lbl) - 1 in lbl)
        self.assertFalse(len(lbl) in lbl)

        # __contains__() with a new key
        self.assertTrue('FOO' in lbl)
        self.assertTrue(('FOO', 'TASK') in lbl)
        self.assertTrue(('FOO', 'TASK', 'FICOR77') in lbl)
        self.assertFalse(('FOO', 'TASK', 'RESLOC') in lbl)
        self.assertTrue(('FOO', 'TASK', 'GEOMA') in lbl)

        self.assertFalse(('BAR', 'TASK') in lbl)
        self.assertFalse(('BAR', 'TASK', 'FICOR77') in lbl)
        self.assertTrue(('BAR', 'TASK', 'RESLOC') in lbl)
        self.assertTrue(('BAR', 'TASK', 'GEOMA') in lbl)

        # __setitem__() with a new key, not existing
        indx = lbl.arg('TASK', 'RESLOC')
        lbl['BAR', 'TASK', 'FICOR77'] = 99  # insertion
        self.assertEqual(lbl.arg(('BAR', 'TASK', 'FICOR77')), indx)
        self.assertTrue(('BAR', 'TASK', 'FICOR77') in lbl)
        names = list(lbl.names())
        self.assertEqual(names[-8:], ['TASK', 'FOO', 'BAR', 'TASK', 'BAR',
                                      'TASK', 'BAR', 'FOO'])

        indx = len(lbl)
        lbl['NEW', 'TASK', 'GEOMA'] = 99
        self.assertEqual(lbl.arg(('NEW', 'TASK', 'GEOMA')), indx)
        self.assertTrue(('NEW', 'TASK', 'GEOMA') in lbl)
        names = list(lbl.names())
        self.assertEqual(names[-9:], ['TASK', 'FOO', 'BAR', 'TASK', 'BAR',
                                      'TASK', 'BAR', 'FOO', 'NEW'])

        # __delitem__() with new key
        del lbl['FOO', 'TASK', 'GEOMA']
        names = list(lbl.names())
        self.assertEqual(names[-3:], ['TASK', 'BAR', 'NEW'])

        # __delitem__(), insert()
        test = VicarLabel()
        ltest = len(test)
        test.insert('FOO=1', 1)
        test.append('FOO=2')
        test.append('FOO=3')
        self.assertEqual(len(test), ltest+3)
        del test['FOO+',1]
        self.assertEqual(len(test), ltest+1)
        self.assertEqual(test[1], 1)

        self.assertRaises(VicarError, test.insert, 'BAR=7', 0)
        self.assertRaises(VicarError, test.__setitem__, 'LBLSIZE', [1,2])
        self.assertRaises(VicarError, test.__setitem__, 'LBLSIZE', 77.)
        self.assertRaises(VicarError, test.__setitem__, 0, [1,2])
        self.assertRaises(VicarError, test.__setitem__, 0, 77.)

##########################################################################################
