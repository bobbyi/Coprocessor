#!/usr/bin/env python
import coprocessor
import unittest

import program


class TestCoprocessor(unittest.TestCase):
    @unittest.skip("hello")
    def test_coprocessor(self):
        self.assertEquals(4, program.square(2))
        self.assertEquals(8, program.add(6, 2))
        self.assertEquals(36, program.product(6, 2, 3))

    def test_import(self):
        program = coprocessor.pypy_import('program')

if __name__ == '__main__':
    unittest.main()
