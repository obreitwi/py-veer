#!/usr/bin/env python
# encoding: utf-8

__all__ = [
    "RemoteError",
]

import itertools as it
import sys
import traceback


# log exceptions to default logger
from .logcfg import log


class RemoteError(Exception):
    "Wrapper for an exception occuring during a remote call."

    def wrap_exception(self):
        """Store information about the current exception within this
        RemoteError-instance so that they can be send to the host.

        This has to be done in a non-__init__ method because otherwise
        automatic pickling would fail.
        """
        E, e, tb = sys.exc_info()

        self.original_error_name = E.__name__
        self.original_error_message = str(e)

        self.formatted_error = traceback.format_exception_only(E, e)
        self.formatted_traceback = traceback.format_list(traceback.extract_tb(tb))

    def write_to_log(self):
        for item in it.chain(self.formatted_traceback, self.formatted_error):
            for line in item.strip().split("\n"):
                log.error(line)

    def __str__(self):
        return f"RemoteError wrapping {self.original_error_name}: {self.original_error_message}"
