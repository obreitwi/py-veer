#!/usr/bin/env python
# encoding: utf-8

import json
import os
import os.path as osp
import unittest
import veer.config


def get_items_recursive(dikt=None, sep=".", prefix=""):
    """Get items from a dict recursively where the keys are fully joined by `sep` so that
    they can be used in `veer.{g,s}et_config`.

    Args:
        dikt: Dictionary to iterate over.

        sep: Separator for full key specification.

        prefix: prefix to use for all keys.

    Yields:
        (key, value) pairs where the key is fully joined.
    """
    for k, v in dikt.items():
        full_key = sep.join([prefix, k])
        if isinstance(v, dict):
            yield from get_items_recursive(dikt=v, sep=sep, prefix=full_key)
        else:
            # omit first sep
            yield full_key[len(sep) :], v


class TestVeerConfig(unittest.TestCase):
    path_test_config_json = osp.join(
        osp.dirname(osp.abspath(__file__)), "test_config.json"
    )
    path_test_config_yaml = osp.join(
        osp.dirname(osp.abspath(__file__)), "test_config.yaml"
    )

    def setUp(self):
        # verify default keys present prior to loading test config
        for key, _ in get_items_recursive(veer.config.defaults):
            self.assertIsNotNone(veer.get_config(key), msg=f"{key} not in config!")

        self._veer_config_userset = os.environ.get("VEER_CONFIG", None)
        os.environ["VEER_CONFIG"] = self.path_test_config_json
        veer.read_set_config()

    def tearDown(self):
        veer.log.debug("Restoring older user config.")
        if self._veer_config_userset is not None:
            os.environ["VEER_CONFIG"] = self._veer_config_userset
        else:
            del os.environ["VEER_CONFIG"]

        veer.read_set_config()

    def test_assert_default_confg(self):
        with open(self.path_test_config_json, "rb") as f:
            config = json.load(f)

        for key, val in get_items_recursive(config):
            self.assertEqual(veer.get_config(key), val)

    def test_readback(self):
        veer.set_config("foo.bar.dead", "beef")

        print(veer.get_config("foo.bar.dead"))
        self.assertTrue(veer.get_config("foo.bar.dead") == "beef")
        self.assertTrue(isinstance(veer.get_config("foo.bar"), dict))
        del veer.get_config("foo.bar")["dead"]
        del veer.get_config("foo")["bar"]
        self.assertTrue(isinstance(veer.get_config("foo.bar"), dict))
        self.assertTrue(veer.get_config("foo.bar.dead") == "beef")

    def test_yaml(self):
        try:
            import yaml
        except ImportError:
            raise unittest.SkipTest("yaml module not found.")

        veer.read_set_config(self.path_test_config_yaml)

        with open(self.path_test_config_yaml, "rb") as f:
            config = yaml.safe_load(f)

        for key, val in get_items_recursive(config):
            self.assertEqual(veer.get_config(key), val)
