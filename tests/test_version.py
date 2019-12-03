#!/usr/bin/env python2
# encoding: utf-8

"""
Test if __version__ can be properly imported and read.
"""

import unittest


class TestVersion(unittest.TestCase):
    def test_import(self):
        import veer

        print(veer.__version__)
