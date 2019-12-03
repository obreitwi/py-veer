#!/usr/bin/env python
# encoding: utf-8

__all__ = ["__version__"]

from pbr.version import VersionInfo

# Check the PBR version module docs for other options than release_string()
__version__ = VersionInfo("veer").release_string()
