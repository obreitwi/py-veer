#!/usr/bin/env python2
# encoding: utf-8

""" These tests require a local configuration setting the default container to
an image present on the current host.

It can be build from the testing_container.def recipe like so:

# singularity build veer_test_container.sif veer_test_container.def
"""

import unittest

import os
import os.path as osp
import veer

FOLDER = osp.abspath(osp.dirname(__file__))
TEST_CONTAINER = osp.join(FOLDER, "veer_test_container.sif")

# needed for nested execution
veer.set_config("default_container.image", TEST_CONTAINER)


@veer.in_container(app="first_app")
def in_first_app(a=None, b=None, c=None):
    return os.environ["SINGULARITY_APPNAME"] == "first_app"


@veer.in_container(image=TEST_CONTAINER, app="second_app")
def in_second_app(a=None, b=None, c=None):
    return os.environ["SINGULARITY_APPNAME"] == "second_app"


@veer.in_container(app="first_app")
def nested(a=None, b=None, c=None):
    if os.environ["SINGULARITY_APPNAME"] != "first_app":
        return False
    return in_second_app()


def check_singularity_env():
    # check if singularity is available
    import distutils.spawn as ds

    singularity_binary = veer.get_config("singularity.binary")
    veer.log.info(singularity_binary)
    if ds.find_executable(singularity_binary) is None:
        raise unittest.SkipTest(
            f"Cannot find singularity executable. Searched for {singularity_binary}"
        )

    if not os.path.isfile(TEST_CONTAINER):
        msg = [f"Did not find {TEST_CONTAINER}!"]

        recipe = osp.extsep.join([osp.splitext(TEST_CONTAINER)[0], "def"])
        msg.append(
            f"Please create it by issuing `singularity build {TEST_CONTAINER} {recipe}`!"
        )
        raise unittest.SkipTest(" ".join(msg))

    return False


class TestRunInContainer(unittest.TestCase):
    def setUp(self):
        veer.read_set_config()
        veer.set_config("default_container.image", TEST_CONTAINER)
        check_singularity_env()

    def tearDown(self):
        veer.config.read_set_config()

    def test_another_app(self):
        self.assertTrue(in_second_app())
        self.assertTrue(in_first_app())

    def test_nested(self):
        raise unittest.SkipTest(
            "Needs custom trusted-container feature in singularity."
        )
        self.assertTrue(nested())
