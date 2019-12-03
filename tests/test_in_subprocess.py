#!/usr/bin/env python
# encoding: utf-8

import os
import random
import unittest
import veer


@veer.in_subprocess
def get_pid_child():
    "Get PID of process the function is run in."
    return os.getpid()


@veer.in_subprocess
def loopback(*args, **kwargs):
    """Return whatever was received to test transfer of arguments and return
    values."""
    return {"args": args, "kwargs": kwargs}


class TestRunInSubprocess(unittest.TestCase):
    def setUp(self):
        random.seed(None)

    def tearDown(self):
        pass

    def test_loopback(self):
        def get_rand():
            return random.randint(1, 4096)

        args = (get_rand(), get_rand(), get_rand())
        kwargs = {"foobar": get_rand(), "barfoo": get_rand()}

        retval = loopback(*args, **kwargs)

        self.assertTrue("args" in retval)
        self.assertTrue("kwargs" in retval)

        self.assertTrue(retval["args"] == args)
        self.assertTrue(retval["kwargs"] == kwargs)

    def test_pid_diff(self):
        pid_parent = os.getpid()
        pid_child = get_pid_child()

        self.assertFalse(pid_parent == pid_child)
