#!/usr/bin/env python
# encoding: utf-8

__all__ = [
    "delete_script_file",
    "in_child",
    "recursive_update_dict",
    "recv_object",
    "send_object",
]

import logging
import os
import pickle as pkl


log = logging.getLogger(__name__)


coding = "utf-8"
token_sync = "VEER_SYNC".encode(coding)


def delete_script_file(script_filename, warn=False):
    try:
        os.remove(script_filename)
        log.debug("Deleted script file.")
    except OSError as e:
        if e.errno == 2:
            if warn:
                # Please note that each file is essentially deleted twice under
                # normal conditions (once in _host and once at the atexit
                # deletion routine). This is done to make sure that the file
                # gets deleted even if there is an error, but also doesn't
                # linger around if several subprocess calls are made over the
                # course of a single run.
                log.warn(
                    "Could not delete temporary script file for "
                    "subprocess: " + script_filename
                )
        else:
            raise e


def in_child():
    """Check if we are in a veer-child

    Returns:
        True if we are in a veer-child, False otherwise.
    """
    return "VEER_PARENT" in os.environ


def recursive_update_dict(merge_into, merge_from):
    """
    Recursively merge one dictionary into another.

    Note #1: Only works for dictionaries right now.

    Note #2: Does not copy the content of `merge_from`. If you plan to reuse, please
    supply a copy!

    Args:
        merge_into (dict): Dictionary that is modified in-place to contain the contents
                           of `merge_from`.

        merge_from (dict): Dictionary that is to be merged into `merge_into`.
    """
    if merge_from is None:
        return

    for k, v in merge_from.items():
        if isinstance(v, dict):
            if (
                k in merge_into and isinstance(merge_into[k], dict)
            ) or k not in merge_into:
                recursive_update_dict(merge_into.setdefault(k, {}), v)
            else:
                raise ValueError(
                    f"{k} in merge_from describes a dictionary, but "
                    f"{k} in merge_into is {merge_into[k]}."
                )
        else:
            merge_into[k] = v


def recv_object(socket, buflen=4096):
    try:
        obj_len = int(socket.recv(buflen).decode(coding))
    except ValueError:
        msg = "Remote computation failed. " "See log further up for details."
        log.error(msg)
        raise IOError(msg)
    sync_after_recv(socket)

    recv_counter = 0
    chunks = []
    while recv_counter < obj_len:
        chunk = socket.recv(buflen)
        if chunk == "":
            raise RuntimeError("Socket connection lost.")

        recv_counter += len(chunk)
        chunks.append(chunk)

    obj = pkl.loads(b"".join(chunks))
    sync_after_recv(socket)

    return obj


def send_object(socket, obj, buflen=4096):
    "send object as pickle over a socket"
    obj_str = pkl.dumps(obj, protocol=-1)
    # first, send the length
    obj_len = len(obj_str)
    if log.getEffectiveLevel() <= logging.DEBUG:
        log.debug(f"Object length: {obj_len}")
    socket.send(str(obj_len).encode(coding))

    sync_after_send(socket)

    send_counter = 0
    while send_counter < obj_len:
        chunk_size = socket.send(obj_str[send_counter:])

        if chunk_size == 0:
            raise RuntimeError("Socket connection lost.")

        send_counter += chunk_size
    sync_after_send(socket)


def sync_after_recv(socket):
    """Perform a sync after we received data via socket."""
    socket.send(token_sync)


def sync_after_send(socket):
    """ Perform a sync after we send data via socket.

    Receive the token (and only the token) from a stream to prevent the next
    token leaking."""
    assert socket.recv(len(token_sync)) == token_sync
