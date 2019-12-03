#!/usr/bin/env python3
# encoding: utf-8

__all__ = [
    "formatters",
    "log",
    "log_to_file",
    "setup_logger",
]


import logging
import os

from . import util

LOGNAME = "veer"
formatters = {
    "verbose": logging.Formatter(
        "%(asctime)s %(levelname)s "
        "%(funcName)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%y-%m-%d %H:%M:%S",
    ),
    "default": logging.Formatter(
        "%(asctime)s %(name)s [%(levelname)s]: %(message)s", datefmt="%y-%m-%d %H:%M:%S"
    ),
}


log = logging.getLogger(LOGNAME)


def set_loglevel(handler, level):
    """Helper function to set loglevel.

    Args:
        handler: logging.Handler instance to set loglevel for.

        level: int or string describing the loglevel. If string the
               corresponding level will be used from logging module.
    """

    if not str(level).isdigit():
        level = getattr(logging, level.upper())
    handler.setLevel(level)


def log_to_file(filename, mode="a", loglevel="info", formatter=None):
    """Adds new file handler with specified filename and mode.

    Args:
        filename: String describing filename to log into.

        mode: String describing which  mode to use for opening the file.

        logelvel: int or string describing what level to log to file.

        formatter: logging.Formatter to use for file logging. Defaults to
                   verbose logcfg.formatters["verbose"].
    """
    if formatter is None:
        formatter = formatters["verbose"]

    handler = logging.FileHandler(filename=filename, mode=mode)
    handler.setFormatter(formatter)
    set_loglevel(formatter, loglevel)
    log.addHandler(handler)


def setup_logger(logger=None, force=False):
    """Convenience function to setup a default logger logging to console.

    If DEBUG is set in environment, enable verbose logging format. If QUIET is
    set in environment, only log WARNING and more severe.

    Args:
        logger: logging.Logger instance - if None the root-Logger will be
                configured.

        force: Boolean. Force configuring logger even if there are handlers
               present.
    """
    if logger is None:
        logger = logging.root

    # stop if logger is configured and user does not force
    if logger.hasHandlers() and not force:
        return

    handler = logging.StreamHandler()

    # We use the default format unless DEBUG is in environment.
    if "DEBUG" in os.environ:
        formatter = formatters["verbose"]
    else:
        formatter = formatters["default"]

    handler.setFormatter(formatter)

    if "DEBUG" in os.environ:
        set_loglevel(logger, "debug")
    elif "QUIET" in os.environ:
        set_loglevel(logger, "warning")
    elif not util.in_child():
        # do not set info logging if we are in the child
        set_loglevel(logger, "info")

    logger.addHandler(handler)


setup_logger(log)
