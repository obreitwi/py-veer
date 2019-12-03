#!/usr/bin/env python
# encoding: utf-8

from .config import get_config, set_config, read_set_config  # noqa: F401
from .core import in_container, in_subprocess  # noqa: F401
from .logcfg import log  # noqa: F401


# Avoid needlessly importing pbr by determining __version__ only if the user explicitly
# requests it.
def __getattr__(name):
    if name == "__version__":
        from ._version import __version__

        return __version__
    raise AttributeError(f"module {__name__} has no attribute {name}")
