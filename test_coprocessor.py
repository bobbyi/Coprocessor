#!/usr/bin/env python
import sys
sys.dont_write_bytecode = True
import coprocessor
import unittest


class TestCoprocessor(unittest.TestCase):
    def tearDown(self):
        super(TestCoprocessor, self).tearDown()
        coprocessor.PyPy.stop()

    def test_importer(self):
        from pypy import sys
        sys.setrecursionlimit(103)
        self.assertEquals(103, sys.getrecursionlimit())

    def test_import(self):
        from pypy import program
        self.assertEquals(4, program.square(2))
        self.assertEquals(8, program.add(6, 2))
        self.assertEquals(36, program.product(6, 2, 3))

    def test_import_error(self):
        with self.assertRaises(SyntaxError):
            from pypy import doesnt_import
        with self.assertRaises(ImportError):
            from pypy import doesnt_exist

    def test_module_state(self):
        from pypy import adder
        self.assertEquals(1, adder.inc())
        self.assertEquals(2, adder.inc())
        self.assertEquals(3, adder.inc())

    def test_stdlib_import(self):
        # Builtin modules
        from pypy import operator, sys
        self.assertEquals(6, operator.mul(3, 2))
        sys.setrecursionlimit(103)
        self.assertEquals(103, sys.getrecursionlimit())
        # Python module
        from pypy import linecache
        this_file = __file__
        if this_file.endswith('.pyc'):
            this_file = this_file[:-1]
        with open(this_file) as f:
            line = f.readlines()[2]
        self.assertEquals(line, linecache.getline(this_file, 3))

    def test_multiple_imports(self):
        from pypy import adder, program
        self.assertEquals(1, adder.inc())
        self.assertEquals(4, program.square(2))
        self.assertEquals(2, adder.inc())
        self.assertEquals(8, program.add(6, 2))

        from pypy import adder
        from pypy import program
        self.assertEquals(3, adder.inc())
        self.assertEquals(36, program.product(6, 2, 3))

    def test_exceptions(self):
        from pypy import program
        with self.assertRaises(TypeError):
            program.square({})
        from pypy import operator
        with self.assertRaises(ZeroDivisionError):
            operator.div(5, 0)
        with self.assertRaises(AttributeError):
            operator.not_an_actual_function(5, 0)

    def test_pass_unpickleable(self):
        import functools
        func = lambda: 3
        functools.partial(func)
        functools.partial(int)

        from pypy import functools
        with self.assertRaises(coprocessor.Unpickleable):
            # We try to pass a non-pickleable object (a lambda)
            functools.partial(func)
        with self.assertRaises(coprocessor.Unpickleable):
            # The argument we try to pass is pickleable,
            # but the object returned isn't
            functools.partial(int)

    def test_raise_unpickleable(self):
        from pypy import program
        with self.assertRaises(Exception):
            program.raise_unpickleable()
        with self.assertRaises(Exception):
            program.raise_unpickleable2()
        self.assertEquals(36, program.product(6, 2, 3))


if __name__ == '__main__':
    unittest.main()
