#!/usr/bin/env python
import unittest

import program


class TestCoprocessor(unittest.TestCase):
    def test_coprocessor(self):
        self.assertEquals(4, program.square(2))
        self.assertEquals(8, program.add(6, 2))
        self.assertEquals(36, program.product(6, 2, 3))

if __name__ == '__main__':
    unittest.main()
