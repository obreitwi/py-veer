#!/usr/bin/env python
# encoding: utf-8

__all__ = [
    "config_entry_to_env_variable",
    "get_config",
    "read_config",
    "read_set_config",
    "set_config",
    "set_default_container_app",
    "set_default_container_image",
]

import copy
import logging
import json
import os
import os.path as osp
from pprint import pformat as pf

from . import util

log = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    log.info("Did not find yaml - loading config files in json format.")
    yaml = None


config_entry_to_env_variable = {
    "singularity.binary": "VEER_SINGULARITY_BINARY",
    "default_container.image": "VEER_CONTAINER_IMAGE",
    "default_container.app": "VEER_CONTAINER_APP",
}

defaults = {
    "singularity": {"binary": "singularity"},
    "python": {"binary": "python"},
}

_config = None


def generate_possible_config_paths():
    """
    Returns a list of possible configuration paths.

    Used by read_config, see its docstring for more info.
    """
    if "VEER_CONFIG" in os.environ:
        yield osp.expanduser(os.environ["VEER_CONFIG"])

    def gen_names(directory):
        if yaml is not None:
            yield osp.join(directory, "veer", "config.yaml")
        yield osp.join(directory, "veer", "config.json")

    yield from gen_names(os.getcwd())

    yield from gen_names(
        osp.expanduser(os.environ.get("XDG_CONFIG_HOME", "$HOME/.config"))
    )

    for dir in os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":"):
        yield from gen_names(osp.expanduser(dir))

    yield from gen_names("/etc")


def get_config(key):
    """Get item from config.

    Note that if the corresponding environment variables are defined, they can
    overwrite the default settings (see `config_entry_to_env_variable` for a
    mapping).

    Args:
        key: String describing item location in config. Different levels are
             separated by dots (e.g., `default_container.image` and
             `default_container.app`).

    Returns:
        value corresponding to given key from config.
    """
    env_var = config_entry_to_env_variable.get(key, None)

    if env_var is not None and env_var in os.environ:
        return os.environ[env_var]

    value = _config

    for part in key.split("."):
        if part in value:
            value = value[part]
        else:
            return None

    # if value is a dictionary, return a copy
    if isinstance(value, dict):
        value = copy.deepcopy(value)
    return value


def read_config(config_path=None):
    """If the argument is `config_path` is `None`, read configuration from typical
    places, i.e. the following locations (descending priority):
    * environment variable `${VEER_CONFIG}` pointing to the exact file
    * `${PWD}/veer/config.{yaml,json}`
    * `${XDG_CONFIG_HOME}/veer/config.{yaml,json}`
    * `${XDG_CONFIG_DIRS}/veer/config.{yaml,json}`

    If `config_path` is not None, read only from the *exact* path config_path points to.

    The config file is yaml (or json) and contains the following (everything is
    optional):
    ```yaml
    singularity:
      binary: <path to singularity binary>

    default_container:
      image: <path to default container>
      app: <name of default container>
    ```

    Args:
        config_path:  String describing explicit path to load config from. Will
                      raise an exception if config does not exist!

    Returns:
        Dictionary containing config.
    """
    load = yaml.safe_load if yaml is not None else json.load

    if config_path is None:
        for conf_file in generate_possible_config_paths():
            try:
                with open(conf_file, "r") as f:
                    return load(f)
            except FileNotFoundError:
                continue
    else:
        with open(config_path, "r") as f:
            return load(f)

    # empty config if non found
    log.debug("No config file found.")
    return {}


def set_config(key, value):
    """
    Manually set an item in the config.

    Args:
        key: String describing item location. Different levels are seperated by
             dots (e.g., `default_container.image` and
             `default_container.app`).
    """
    target = _config
    all_parts = key.split(".")
    for part in all_parts[:-1]:
        target = target.setdefault(part, {})
    target[all_parts[-1]] = value


def read_set_config(filename=None):
    """
    Read and set configuration from `filename`.

    Args:
        filename: File to read. If omitted, search the typical places (see
                  `read_config`).
    """
    global _config
    _config = copy.deepcopy(defaults)
    if log.getEffectiveLevel() <= logging.DEBUG:
        log.debug("Set defaults: {}".format(pf(_config)))
    util.recursive_update_dict(_config, read_config(filename))


def set_default_container_app(app):
    """Convenience function to set the default container app.

    Args:
        app: String describing the to be set default app.
    """
    set_config("default_container.app", app)


def set_default_container_image(image):
    """Convenience function to set the default container image.

    Args:
        image: String describing path to the default image.
    """
    set_config("default_container.image", image)


if _config is None:
    read_set_config()
