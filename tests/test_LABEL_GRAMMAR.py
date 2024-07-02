################################################################################
# tests/test_LABEL_GRAMMAR.py
################################################################################

import unittest
from vicar._LABEL_GRAMMAR import _LABEL_GRAMMAR

from pyparsing import ParseException


class Test_LABEL_GRAMMAR(unittest.TestCase):

    def test_LABEL_GRAMMAR(self):

        text = "LBLSIZE=1536  FORMAT   = 'BYTE'   \0\0"
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('LBLSIZE', 1536),
                                  ('FORMAT', 'BYTE', 3, 1, 3)])

        text = "LBLSIZE=1536  FORMAT   = 'BYTE'   \0\0"
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('LBLSIZE', 1536),
                                  ('FORMAT', 'BYTE', 3, 1, 3)])

        text = "A=0  B=00  C=+0  D=+1  E=-1  F=-01  G=+01  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('A', 0),
                                  ('B', 0, '%02d'),
                                  ('C', 0, '%+d'),
                                  ('D', 1, '%+d'),
                                  ('E', -1),
                                  ('F', -1, '%03d'),
                                  ('G', 1, '%+03d')])

        text = "TBPPXL=0.0  INA=77.7883  SOLRANGE=7.43341e+08  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('TBPPXL', 0., '%#.1f'),
                                  ('INA', 77.7883, '%#.4f'),
                                  ('SOLRANGE', 7.43341e+08, '%#.5E')])

        text = "A=1D5  B=+1d4  C=2.E2  D=.1e1  E=+.1e1  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('A', 100000., '%#.0E'),
                                  ('B', 10000., '%#+.0E'),
                                  ('C', 200., '%#.0E'),
                                  ('D', 1., '%#.0E'),
                                  ('E', 1., '%#+.0E')])
        for t in tuples:
            self.assertIsInstance(t[1], float)

        text = "DIGITS=(1, 2,03 , 004 )  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('DIGITS', [1,(2,1,0),(3,'%02d',1),(4,'%03d',1,1)])])

        text = "GROUPS=('LINE','SAMP','C_POS_IMAGE','INPUT')  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('GROUPS', ['LINE','SAMP','C_POS_IMAGE','INPUT'])])
        self.assertIsInstance(tuples[0][1], list)

        text = "GROUPS=('LINE', 'SAMP' ,'C_POS_IMAGE','INPUT')  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('GROUPS', ['LINE',('SAMP',1,1),'C_POS_IMAGE',
                                              'INPUT'])])
        self.assertIsInstance(tuples[0][1], list)

        text = "GROUPS   =('LINE','SAMP','C_POS_IMAGE','INPUT')  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('GROUPS', ['LINE','SAMP','C_POS_IMAGE','INPUT'],
                                   3, 0, 2)])
        self.assertIsInstance(tuples[0][1], list)

        text = "GROUPS=   ('LINE','SAMP','C_POS_IMAGE','INPUT')  "
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('GROUPS', ['LINE','SAMP','C_POS_IMAGE','INPUT'],
                                   3, 2)])
        self.assertIsInstance(tuples[0][1], list)

        text = 'A2345678901234567890123456789012=7'
        tuples = _LABEL_GRAMMAR.parse_string(text).as_list()
        self.assertEqual(tuples, [('A2345678901234567890123456789012', 7, 0)])

        # Exceptions

        # Test removed because we allow longer names now
        #     text = 'A23456789012345678901234567890123=7'
        #     self.assertRaises(ParseException, _LABEL_GRAMMAR.parse_string, text)

        text = '_123=7'
        self.assertRaises(ParseException, _LABEL_GRAMMAR.parse_string, text)

        text = "GROUPS=('LINE','SAMP','C_POS_IMAGE','INPUT',)  "
        self.assertRaises(ParseException, _LABEL_GRAMMAR.parse_string, text)
