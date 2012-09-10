#!/usr/bin/env python
import sys
sys.dont_write_bytecode = True
import coprocessor
import unittest


class TestCoprocessor(unittest.TestCase):
    def setUp(self):
        super(TestCoprocessor, self).setUp()
        self.co = coprocessor.CoProcessor()
        self.addCleanup(self.co.close)

    def test_import(self):
        program = self.co.import_module('program')
        self.assertEquals(4, program.square(2))
        self.assertEquals(8, program.add(6, 2))
        self.assertEquals(36, program.product(6, 2, 3))

    def test_adder(self):
        adder = self.co.import_module('adder')
        self.assertEquals(1, adder.inc())
        self.assertEquals(2, adder.inc())
        self.assertEquals(3, adder.inc())

    def test_stdlib_import(self):
        # Builtin modules
        operator = self.co.import_module('operator')
        self.assertEquals(6, operator.mul(3, 2))
        sys = self.co.import_module('sys')
        sys.setrecursionlimit(103)
        self.assertEquals(103, sys.getrecursionlimit())
        # Python module
        linecache = self.co.import_module('linecache')
        this_file = __file__
        if this_file.endswith('.pyc'):
            this_file = this_file[:-1]
        with open(this_file) as f:
            line = f.readlines()[2]
        self.assertEquals(line, linecache.getline(this_file, 3))

    def test_multiple_imports(self):
        adder = self.co.import_module('adder')
        program = self.co.import_module('program')
        self.assertEquals(1, adder.inc())
        self.assertEquals(4, program.square(2))
        self.assertEquals(2, adder.inc())
        self.assertEquals(8, program.add(6, 2))

        adder = self.co.import_module('adder')
        program = self.co.import_module('program')
        self.assertEquals(3, adder.inc())
        self.assertEquals(36, program.product(6, 2, 3))

    def test_exceptions(self):
        program = self.co.import_module('program')
        with self.assertRaises(TypeError):
            program.square({})
        operator = self.co.import_module('operator')
        with self.assertRaises(ZeroDivisionError):
            operator.div(5, 0)

    def test_unpickleable(self):
        program = self.co.import_module('program')
        with self.assertRaises(coprocessor.Unpickleable):
            program.raise_unpickleable()
        with self.assertRaises(coprocessor.Unpickleable):
            program.raise_unpickleable2()


if __name__ == '__main__':
    unittest.main()
