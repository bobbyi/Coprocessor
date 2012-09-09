#!/usr/bin/env python
import coprocessor
import unittest

class TestCoprocessor(unittest.TestCase):
    def test_import(self):
        co = coprocessor.CoProcessor()
        self.addCleanup(co.close)
        program = co.import_module('program')
        self.assertEquals(4, program.square(2))
        self.assertEquals(8, program.add(6, 2))
        self.assertEquals(36, program.product(6, 2, 3))

    def test_adder(self):
        co = coprocessor.CoProcessor()
        self.addCleanup(co.close)
        adder = co.import_module('adder')
        self.assertEquals(1, adder.inc())
        self.assertEquals(2, adder.inc())
        self.assertEquals(3, adder.inc())

if __name__ == '__main__':
    unittest.main()
