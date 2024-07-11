##########################################################################################
# tests/test_vicarimage.py
##########################################################################################

import io
import numpy as np
import os
import pathlib
import unittest
import sys
from contextlib import redirect_stdout
from vicar.vicarimage import VicarImage
from vicar.vicarlabel import VicarError


class Test_VicarImage(unittest.TestCase):

    def test_VicarImage(self):

        # _intfmt
        sysval = 'LOW' if sys.byteorder == 'little' else 'HIGH'
        self.assertEqual(VicarImage._intfmt(np.arange(10, dtype='<i8')), 'LOW')
        self.assertEqual(VicarImage._intfmt(np.arange(10, dtype='>i8')), 'HIGH')
        self.assertEqual(VicarImage._intfmt(np.arange(10, dtype='<f8')), 'LOW')
        self.assertEqual(VicarImage._intfmt(np.arange(10, dtype='>f8')), 'HIGH')
        self.assertEqual(VicarImage._intfmt(np.arange(10)), sysval)
        self.assertEqual(VicarImage._intfmt(np.arange(10, dtype='uint8')), sysval)

        # _realfmt
        sysval = 'RIEEE' if sys.byteorder == 'little' else 'IEEE'
        self.assertEqual(VicarImage._realfmt(np.arange(10, dtype='<i8')), 'RIEEE')
        self.assertEqual(VicarImage._realfmt(np.arange(10, dtype='>i8')), 'IEEE')
        self.assertEqual(VicarImage._realfmt(np.arange(10, dtype='<f8')), 'RIEEE')
        self.assertEqual(VicarImage._realfmt(np.arange(10, dtype='>f8')), 'IEEE')
        self.assertEqual(VicarImage._realfmt(np.arange(10.)), sysval)
        self.assertEqual(VicarImage._realfmt(np.arange(10, dtype='uint8')), sysval)

        # _format_isint
        self.assertEqual(VicarImage._format_isint(np.arange(10, dtype='uint8')), ('BYTE', True))
        self.assertEqual(VicarImage._format_isint(np.arange(10., dtype='<f4')), ('REAL', False))
        self.assertEqual(VicarImage._format_isint(np.arange(10., dtype='>f4')), ('REAL', False))
        self.assertRaises(VicarError, VicarImage._format_isint, np.arange(10., dtype='c16'))

        # _check_array_vs_prefix
        VicarImage._check_array_vs_prefix(None, None)
        VicarImage._check_array_vs_prefix(np.zeros((1,100,200)), None)
        VicarImage._check_array_vs_prefix(np.zeros((100,200,300)), None)
        VicarImage._check_array_vs_prefix(None, np.zeros((100,200,300)))
        VicarImage._check_array_vs_prefix(np.zeros((1,100,200)), np.zeros((1,100,20)))
        VicarImage._check_array_vs_prefix(np.zeros((100,200,30)), np.zeros((100,200,30)))
        VicarImage._check_array_vs_prefix(np.zeros((1,200,100), dtype='uint8'),
                                          np.zeros((1,200,20), dtype='<i4'))
        VicarImage._check_array_vs_prefix(np.zeros((1,200,100), dtype='<i4'),
                                          np.zeros((1,200,20), dtype='uint8'))
        VicarImage._check_array_vs_prefix(np.zeros((1,200,100), dtype='<f4'),
                                          np.zeros((1,200,20), dtype='uint8'))
        VicarImage._check_array_vs_prefix(np.zeros((1,200,100), dtype='<f4'),
                                          np.zeros((1,200,20), dtype='>i2'))
        VicarImage._check_array_vs_prefix(np.zeros((1,200,100), dtype='<f8'),
                                          np.zeros((1,200,20), dtype='<f4'))
        VicarImage._check_array_vs_prefix(np.zeros((1,200,100), dtype='<i4'),
                                          np.zeros((1,200,20), dtype='<i2'))

        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          np.arange(10), None)
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          None, np.arange(10))
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          np.zeros((10,10)), None)
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          None, np.zeros((10,10)))
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          np.zeros((10,10,10,10)), None)
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          np.zeros((1,100,100)),np.zeros((1,200,10)))
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          np.zeros((1,200,100), dtype='>i4'),
                          np.zeros((1,200,20), dtype='<i4'))
        self.assertRaises(VicarError, VicarImage._check_array_vs_prefix,
                          np.zeros((1,200,100), dtype='>f4'),
                          np.zeros((1,200,20), dtype='<f4'))

        # Reading image file C0532836239R.IMG
        vicar_dir = pathlib.Path(sys.modules['vicar'].__file__)
        test_dir = vicar_dir.parent.parent / 'test_files'
        filepath = test_dir / 'C0532836239R.IMG'

        vim = VicarImage(filepath)

        self.assertEqual(vim['NL'], 800)
        self.assertEqual(vim['TRUTH_WINDOW'], [801,801,96,96])
        self.assertEqual(vim['COMPRESSION_RATIO'], 9.64155)
        self.assertEqual(vim['SOLRANGE'], 7.43341E+08)
        self.assertEqual(vim['TARGET'], 'EUROPA')
        self.assertEqual(vim.as_dict()['TARGET'], 'EUROPA')

        self.assertEqual(vim.array.shape, (1, 800, 800))
        self.assertEqual(vim.array3d.shape, (1, 800, 800))
        self.assertEqual(vim.data_3d.shape, (1, 800, 800))
        self.assertEqual(vim.array2d.shape, (800, 800))
        self.assertEqual(vim.data_2d.shape, (800, 800))

        image = vim.array2d
        self.assertEqual(image.shape, (800,800))
        self.assertEqual(image.dtype, np.dtype('uint8'))
        self.assertEqual(image[367,371], 220)

        self.assertEqual(vim['NLB'], 6)
        bh = vim.binheader_array(kind='u', size=2)
        self.assertEqual(bh.size, 6 * vim['RECSIZE'] / 2)
        self.assertEqual(bh.dtype, np.dtype('<u2'))

        self.assertEqual(vim['NBB'], 200)
        self.assertEqual(vim.prefix.shape, (1, 800, 200))
        self.assertEqual(vim.prefix_3d.shape, (1, 800, 200))
        self.assertEqual(vim.prefix3d.shape, (1, 800, 200))
        self.assertEqual(vim.prefix_2d.shape, (800, 200))
        self.assertEqual(vim.prefix2d.shape, (800, 200))

        # from_file
        vim2 = VicarImage.from_file(filepath)
        self.assertEqual(vim, vim2)
        self.assertRaises(VicarError, VicarImage.from_file, filepath, extraneous='error')
        self.assertWarns(UserWarning, VicarImage.from_file, filepath, extraneous='warn')

        extra = VicarImage.from_file(filepath, extraneous='include')[-1]
        self.assertEqual(len(extra), 23488)
        self.assertTrue(all(c == 0 for c in extra))

        self.assertRaises(ValueError, VicarImage.from_file, filepath, extraneous='???')

        with io.StringIO() as buf, redirect_stdout(buf):
            VicarImage.from_file(filepath, extraneous='print')
            output = buf.getvalue()
            self.assertIn('has 23488 zero-valued trailing bytes', output)

        # filepath property
        vim.filepath = None
        self.assertEqual(vim.filepath, None)
        vim.filepath = str(filepath)
        self.assertEqual(vim.filepath, filepath)
        self.assertIsInstance(vim.filepath, pathlib.Path)

        # binheader
        test = VicarImage(test_dir / 'C2069302_GEOMA.DAT')
        self.assertIsNone(test.array)
        self.assertIsNone(test.array2d)
        self.assertIsNone(test.array3d)
        self.assertIsNone(test.prefix)
        self.assertIsNone(test.prefix2d)
        self.assertIsNone(test.prefix3d)
        array = test.binheader_array()
        self.assertEqual(array.shape, (552,4))
        self.assertEqual(array.dtype, np.dtype('=f4'))
        self.assertTrue(np.all(array[0] == np.array([25.11, 25.29, 24.076107, 11.095002],
                                                    dtype='float32')))
        self.assertTrue(np.all(array[2] == np.array([20.33, 85.48, 14.932872, 57.43326],
                                                    dtype='float32')))

        # Messing around with arrays, write_file
        with self.assertRaises(VicarError):
            test.array = np.random.randn(100,100)   # incompatible with binheader

        test.array = np.random.randn(2,50,72).astype('f4')
        self.assertEqual(test['RECSIZE'], 288)

        with self.assertRaises(VicarError):
            test.prefix = np.random.randint(0, 256, (2,50,287), dtype='uint8')

        test.prefix = np.random.randint(0, 256, (2,50,288), dtype='uint8')
        self.assertEqual(test['RECSIZE'], 576)

        dest = test_dir / 'C2069302_GEOMA_with_image.DAT'
        test.write_file(dest)
        test2 = VicarImage.from_file(dest)
        self.assertEqual(test2.label, test.label)
        self.assertTrue(np.all(test.array3d == test2.array3d))
        self.assertTrue(np.all(test.prefix3d == test2.prefix3d))
        self.assertEqual(test.binheader, test2.binheader)

        with self.assertRaises(VicarError):
            _ = test.array2d

        with self.assertRaises(VicarError):
            _ = test.prefix2d

        os.remove(dest)

        # indexing
        self.assertEqual(len(test), len(test._label))
        self.assertIn('RECSIZE', test)
        self.assertEqual(test['BUFSIZ'], 20480)
        self.assertEqual(test.get('BUFSIZ',0), 20480)
        self.assertEqual(test.get('WHATEVER',7), 7)
        self.assertRaises(VicarError, test.__setitem__, 'RECSIZE', 100)
        self.assertRaises(VicarError, test.__setitem__, ('RECSIZE',0), 100)
        self.assertRaises(VicarError,  test.__setitem__, test.arg('RECSIZE'), 100)
        self.assertRaises(VicarError, test.__delitem__, 'RECSIZE')
        self.assertRaises(VicarError, test.__delitem__, ('RECSIZE',0))
        self.assertRaises(VicarError,  test.__delitem__, test.arg('RECSIZE'))
        self.assertEqual(str(test), str(test._label))
        self.assertEqual(repr(test)[10:], repr(test._label)[10:])
        self.assertEqual(len(test), len([key for key in test]))

        test['RECSIZE+'] = 77
        self.assertRaises(VicarError, test.__setitem__, 'RECSIZE', 100)
        self.assertRaises(VicarError, test.__delitem__, 'RECSIZE')
        test['RECSIZE',1] = 99
        del test['RECSIZE',1]
        self.assertRaises(VicarError, test.__setitem__, 'RECSIZE', 100)
        self.assertRaises(VicarError, test.__delitem__, 'RECSIZE')

        # iterators
        self.assertEqual(list(test)[:3], ['LBLSIZE', 'FORMAT', ('TYPE',0)])

        self.assertEqual(list(test.names('TASK')), ['TASK', 'TASK', 'TASK'])
        self.assertEqual(list(test.names())[:3], ['LBLSIZE', 'FORMAT', 'TYPE'])

        self.assertEqual(list(test.keys('TASK')), [('TASK',0), ('TASK',1), ('TASK',2)])
        self.assertEqual(list(test.keys())[:3], ['LBLSIZE', 'FORMAT', ('TYPE',0)])

        self.assertEqual(list(test.values('TASK')), ['TASK', 'VGRFILLI', 'RESLOC'])
        self.assertEqual(list(test.values())[:3], [2304, 'REAL', 'IMAGE'])

        self.assertEqual(list(test.items('TASK', unique=False)),
                         [('TASK','TASK'), ('TASK','VGRFILLI'), ('TASK','RESLOC')])
        self.assertEqual(list(test.items('TASK', unique=True)),
                         [(('TASK',0), 'TASK'), (('TASK',1), 'VGRFILLI'),
                          (('TASK',2), 'RESLOC')])
        self.assertEqual(list(test.items(unique=False))[:3],
                         [('LBLSIZE', 2304), ('FORMAT', 'REAL'), ('TYPE', 'IMAGE')])
        self.assertEqual(list(test.items(unique=True))[:3],
                         [('LBLSIZE', 2304), ('FORMAT', 'REAL'), (('TYPE',0), 'IMAGE')])

        self.assertEqual(list(test.items(r'GROUP_\d+')), [('GROUP_1', [3, 1]),
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
        self.assertEqual(list(test.values(r'GROUP_\d+')), [[3, 1],
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

        self.assertEqual(list(test.args(r'GROUP_\d+')), list(range(31,42)))
        self.assertEqual(list(test.args()), list(range(70)))

        len0 = len(test)
        last_dat_time = test[('DAT_TIM',-1)]
        del test[('DAT_TIM',-1)]
        self.assertEqual(len(test), len0-1)
        test['DAT_TIM+'] = last_dat_time
        self.assertEqual(len(test), len0)

        # Reading image file C2069302_GEOMED.IMG
        filepath = test_dir / 'C2069302_GEOMED.IMG'
        vim = VicarImage(filepath)

        self.assertRaises(IndexError, vim.__getitem__, ('LBLSIZE',1))
        self.assertEqual(vim.binheader, None)
        self.assertEqual(vim.prefix, None)

        with self.assertRaises(VicarError):
            vim.binheader = np.random.randint(0, 256, 2001, dtype='uint8')

        with self.assertRaises(VicarError):
            vim.binheader = bytes(np.random.randint(0, 256, 2001, dtype='uint8'))

        with self.assertRaises(VicarError):
            vim.binheader = np.random.randint(0, 256, 2001, dtype='uint8').data

        vim.binheader = np.random.randint(0, 256, 2000, dtype='uint8')

        with self.assertRaises(VicarError):
            vim.prefix = np.random.randint(0, 32000, (1000,2), dtype='int16')

        vim.binheader = None
        vim.prefix = np.random.randint(0, 32000, (1000,2), dtype='int16')
        vim.binheader = np.random.randint(0, 256, 2004, dtype='uint8')

        dest = test_dir / 'C2069302_GEOMED_with_prefix.IMG'
        vim.write_file(dest)
        vim2 = VicarImage(dest)
        self.assertEqual(vim, vim2)

        with self.assertRaises(VicarError):
            vim.prefix = None

        vim.binheader = None
        vim.prefix = None
        vim.write_file(dest)
        vim2 = VicarImage(dest)
        self.assertEqual(vim, vim2)

        os.remove(dest)

        # Start from scratch
        vim = VicarImage()
        dest = test_dir / 'temp.IMG'
        self.assertRaises(VicarError, vim.write_file, dest)

        vim.prefix = np.random.randint(0, 32000, (100,10)).astype('>i2')
        self.assertEqual(vim['INTFMT'], 'HIGH')
        vim.prefix = np.random.randint(0, 32000, (100,10)).astype('<i2')
        self.assertEqual(vim['INTFMT'], 'LOW')
        vim.prefix = np.random.randint(0, 32000, (100,10)).astype('>i2')
        self.assertEqual(vim['INTFMT'], 'HIGH')

        vim.prefix = np.random.randn(100,10).astype('>f8')
        self.assertEqual(vim['REALFMT'], 'IEEE')
        vim.prefix = np.random.randn(100,10).astype('<f8')
        self.assertEqual(vim['REALFMT'], 'RIEEE')
        vim.prefix = np.random.randn(100,10).astype('>f8')
        self.assertEqual(vim['REALFMT'], 'IEEE')

        vim.binheader = np.random.randint(0, 32000, (100,10)).astype('>i2')
        self.assertEqual(vim['BINTFMT'], 'HIGH')
        vim.binheader = np.random.randint(0, 32000, (100,10)).astype('<i2')
        self.assertEqual(vim['BINTFMT'], 'LOW')
        vim.binheader = np.random.randint(0, 32000, (100,10)).astype('>i2')
        self.assertEqual(vim['BINTFMT'], 'HIGH')

        vim.binheader = np.random.randn(100,10).astype('>f4')
        self.assertEqual(vim['BREALFMT'], 'IEEE')
        vim.binheader = np.random.randn(100,10).astype('<f4')
        self.assertEqual(vim['BREALFMT'], 'RIEEE')
        vim.binheader = np.random.randn(100,10).astype('>f4')
        self.assertEqual(vim['BREALFMT'], 'IEEE')

        self.assertEqual(vim['BHOST'], vim['HOST'])

        vim.prefix = None
        vim.binheader = None

        vim.array = np.random.randint(0, 32000, (200,100)).astype('>i2')
        self.assertEqual(vim['INTFMT'], 'HIGH')
        vim.array = np.random.randint(0, 32000, (200,100)).astype('<i2')
        self.assertEqual(vim['INTFMT'], 'LOW')
        vim.array = np.random.randint(0, 32000, (200,100)).astype('>i2')
        self.assertEqual(vim['INTFMT'], 'HIGH')
        self.assertEqual(vim['NS'], 100)
        self.assertEqual(vim['N1'], 100)
        self.assertEqual(vim['NL'], 200)
        self.assertEqual(vim['N2'], 200)
        self.assertEqual(vim['N3'], 1)
        self.assertEqual(vim['NBB'], 0)
        self.assertEqual(vim['NLB'], 0)
        self.assertEqual(vim['RECSIZE'], 200)

        vim.binheader = np.random.randn(2,100).astype('>f4')
        self.assertEqual(vim['BREALFMT'], 'IEEE')
        vim.binheader = np.random.randn(2,100).astype('<f4')
        self.assertEqual(vim['BREALFMT'], 'RIEEE')
        vim.binheader = np.random.randn(2,100).astype('>f4')
        self.assertEqual(vim['BREALFMT'], 'IEEE')
        self.assertEqual(vim['NLB'], 4)

        vim.binheader = None

        with self.assertRaises(VicarError):
            vim.prefix = np.random.randint(0, 32000, (200,10)).astype('<i2')

        vim.prefix = np.random.randint(0, 32000, (200,10)).astype('>i2')
        self.assertEqual(vim['NLB'], 0)
        self.assertEqual(vim['RECSIZE'], 220)

        vim.binheader = np.random.randn(2,55).astype('>f4')
        self.assertEqual(vim['BREALFMT'], 'IEEE')
        vim.binheader = np.random.randn(2,55).astype('<f4')
        self.assertEqual(vim['BREALFMT'], 'RIEEE')
        vim.binheader = np.random.randn(2,55).astype('>f4')
        self.assertEqual(vim['BREALFMT'], 'IEEE')

        self.assertTrue(np.all(vim.binheader == vim.binheader_array(kind='f')))

        saved = vim.binheader
        vim.binheader = bytes(saved)
        array = vim.binheader_array(kind='f', size=4).reshape(2,55)
        self.assertTrue(np.all(saved == array))

        vim.binheader = None
        self.assertEqual(vim.binheader_array(), None)

        # Start from float array
        vim = VicarImage.from_array(np.random.randn(3,100,100).astype('>f8'))
        self.assertEqual(vim['REALFMT'], 'IEEE')
        vim = VicarImage.from_array(np.random.randn(3,100,100).astype('<f8'))
        self.assertEqual(vim['REALFMT'], 'RIEEE')
        vim = VicarImage.from_array(np.random.randn(3,100,100).astype('>f8'))
        self.assertEqual(vim['REALFMT'], 'IEEE')
        self.assertEqual(vim['NB'], 3)
        self.assertEqual(vim['NL'], 100)
        self.assertEqual(vim['NS'], 100)
        self.assertEqual(vim['FORMAT'], 'DOUB')

        vim.label['INTFMT'] = 'HIGH'    # override
        vim.prefix = np.random.randint(0, 255, (3,100,10)).astype('u1')
        self.assertEqual(vim['INTFMT'], 'HIGH')

        vim.label['INTFMT'] = 'LOW'     # override
        vim.prefix = np.random.randint(0, 255, (3,100,10)).astype('u1')
        self.assertEqual(vim['INTFMT'], 'LOW')

        vim.prefix = np.random.randint(0, 32000, (3,100,10)).astype('>i2')
        self.assertEqual(vim['INTFMT'], 'HIGH')
        vim.prefix = np.random.randint(0, 32000, (3,100,10)).astype('<i2')
        self.assertEqual(vim['INTFMT'], 'LOW')

        with self.assertRaises(VicarError):
            vim.prefix = np.random.randn(3,100,100).astype('<f8')

        vim.prefix = np.random.randn(3,100,100).astype('>f4')
        self.assertEqual(vim['FORMAT'], 'DOUB')     # unchanged

        # Start from int array
        vim = VicarImage.from_array(np.random.randint(-1000, 1000, (100,100)).astype('<i4'))
        self.assertEqual(vim['INTFMT'], 'LOW')
        vim = VicarImage.from_array(np.random.randint(-1000, 1000, (100,100)).astype('>i4'))
        self.assertEqual(vim['INTFMT'], 'HIGH')
        vim = VicarImage.from_array(np.random.randint(-1000, 1000, (100,100)).astype('<i4'))
        self.assertEqual(vim['INTFMT'], 'LOW')
        self.assertEqual(vim['NB'], 1)
        self.assertEqual(vim['NL'], 100)
        self.assertEqual(vim['NS'], 100)
        self.assertEqual(vim['FORMAT'], 'FULL')

        vim.prefix = np.random.randn(100,10).astype('>f4')
        self.assertEqual(vim['REALFMT'], 'IEEE')
        vim.prefix = np.random.randn(100,10).astype('<f4')
        self.assertEqual(vim['REALFMT'], 'RIEEE')
        vim.prefix = np.random.randn(100,10).astype('>f4')
        self.assertEqual(vim['REALFMT'], 'IEEE')

        with self.assertRaises(VicarError):
            vim.prefix = np.random.randint(0, 32000, (100,100)).astype('>i2')

        vim.prefix = np.random.randint(0, 32000, (100,100)).astype('<i2')
        self.assertEqual(vim['FORMAT'], 'FULL')     # unchanged

        # copy, eq
        filepath = test_dir / 'C2069302_GEOMED.IMG'
        vim = VicarImage(filepath)
        vim2 = vim.copy()
        self.assertEqual(vim, vim2)
        self.assertIs(vim.array, vim2.array)
        self.assertIsNot(vim, vim2)

        vim2.array = None
        self.assertIs(vim2.array, None)
        self.assertIsNot(vim.array, None)

        vim3 = VicarImage(vim2.label)
        vim2.prefix = None
        vim2.binheader = None
        self.assertEqual(vim2, vim3)

        vim2 = vim.deepcopy()
        self.assertIsNot(vim, vim2)
        self.assertIsNot(vim.array, vim2.array)
        self.assertTrue(np.all(vim.array == vim2.array))

        self.assertNotEqual(vim, set())

        # Reading image file C0532836239R.IMG, with overrides
        filepath = test_dir / 'C0532836239R.IMG'
        array = np.random.randn(1999,200).astype('<f4')

        with self.assertRaises(VicarError):
            vim = VicarImage(filepath, array=np.random.randn(100,100).astype('<f4'))

        with self.assertRaises(VicarError):
            vim = VicarImage(filepath, prefix=np.random.randn(100,100).astype('<f4'))

        with self.assertRaises(VicarError):
            vim = VicarImage(filepath, binheader=1999 * b'\0')

        binheader = 2000 * b'\0'
        vim = VicarImage(filepath, binheader=binheader)
        self.assertEqual(vim.binheader, binheader)

        prefix = np.random.randn(800,10).astype('<f4')
        with self.assertRaises(VicarError):
            vim = VicarImage(filepath, prefix=prefix)

        binheader = 840 * b'1'
        vim = VicarImage(filepath, prefix=prefix, binheader=binheader)
        self.assertTrue(np.all(vim.prefix2d.view(dtype='<f4') == prefix))
        self.assertEqual(vim.binheader, binheader)

        array = np.random.randint(0, 255, (1,800,800)).astype('u1')
        vim = VicarImage(filepath, array=array)
        self.assertTrue(np.all(vim.array == array))

        with self.assertRaises(VicarError):
            vim = VicarImage(filepath, array=array, prefix=prefix)

        vim = VicarImage(filepath, array=array, prefix=prefix, binheader=b'')
        self.assertTrue(np.all(vim.array == array))
        self.assertTrue(np.all(vim.prefix2d.view(dtype='<f4') == prefix))
        self.assertIsNone(vim.binheader)

        vim = VicarImage(filepath, binheader=b'')
        self.assertEqual(vim.array.shape, (1,800,800))
        self.assertTrue(vim.prefix2d.shape, (800,200))
        self.assertIsNone(vim.binheader)

        vim = VicarImage(filepath, prefix=[], binheader=b'')
        self.assertEqual(vim.array.shape, (1,800,800))
        self.assertIsNone(vim.prefix2d)
        self.assertIsNone(vim.binheader)

        # Add some "strict" tests

        filepath = test_dir / 'N1536633072_1_CALIB.IMG'
        self.assertRaises(VicarError, VicarImage, filepath)

        vim = VicarImage(filepath, strict=False)
        self.assertEqual(vim['UNEVEN_BIT_WEIGHT_CORRECTION_FLAG'], 1)

        filepath = test_dir / 'C0003061900R.IMG'
        self.assertRaises(VicarError, VicarImage, filepath)

        vim = VicarImage(filepath, strict=False)
        self.assertEqual(vim['BARC'], 'IP\x80')

##########################################################################################
