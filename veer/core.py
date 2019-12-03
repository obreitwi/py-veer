#!/usr/bin/env python
# encoding: utf-8

__all__ = [
    "in_subprocess",
    "in_container",
]

import atexit
import distutils.spawn as ds
import logging
import os
import os.path as osp
import socket as skt
import subprocess as sp
import sys
import tempfile

from . import util
from .config import get_config
from .exception import RemoteError

log = logging.getLogger(__name__)


def in_container(image=None, app=None):
    """Wrapper to execute given function in a singularity container image
    explicitly.

    Args:
        image: String containing a path to the singluarity image to be used. If
               None the default container will be used.

        app: String pointing to the singluarity image to be used. If None the
             default container will be used.
    """

    def _wrapper(func):
        return Veerify(
            func, container_image=image, container_app=app, always_in_container=True
        )

    return _wrapper


def in_subprocess(func):
    """A functor that replaces the original function.

    If VEER_SINGULARITY is defined or VEER_CONTAINER_IMAGE and
    VEER_CONTAINER_APP are defined, the subprocess is run in a singularity
    container.

    If VEER_SINGULARITY is defined, functions are run with the app
    `visionary-simulations` in the container `/containers/stable/latest`
    (VEER_CONTAINER_APP/VEER_CONTAINER_IMAGE can be used to overwrite this.

    If functions should always be executed in containers, use
    `run_in_container` instead.
    """
    return Veerify(func)


class Veerify(object):
    """
        A functor that replaces the original function.

        If VEER_SINGULARITY is defined or VEER_CONTAINER_IMAGE and
        VEER_CONTAINER_APP are defined, the subprocess is run in a singularity
        container.

        If VEER_SINGULARITY is defined, functions are run with the app
        `visionary-simulations` in the container `/containers/stable/latest`
        (VEER_CONTAINER_APP/VEER_CONTAINER_IMAGE can be used to overwrite this.

        If functions should always be executed in containers, use
        `RunInContainer` instead.
    """

    def __call__(self, *args, **kwargs):
        if "DEBUG" in os.environ or "VEER_NO_SUBPROCESS" in os.environ:
            return self._func(*args, **kwargs)
        else:
            return self._host(*args, **kwargs)

    def __init__(
        self, func, container_image=None, container_app=None, always_in_container=False
    ):
        """
        The following kwargs apply to RunInContainer:

        container_image: path of container image to run function in
        container_app: name of container app in which to run function
        always_in_container: if True we always run in container

        If they are not given, all RunInSubprocess-decorated functions can be
        run in a singularity container by setting VEER_SINGULARITY and
        specifying VEER_CONTAINER_IMAGE / VEER_CONTAINER_APP.

        Note: singularity binary needs to be in path!
        """
        self._func = func
        self.__doc__ = getattr(func, "__doc__", "")

        self._func_name = func.__name__
        self.__name__ = f"{self._func_name}.veerified"
        self._func_module = func.__module__

        self._container_image = container_image
        self._container_app = container_app
        self._always_in_container = always_in_container

        try:
            self._func_dir = self._get_func_dir(self._func_module)
        except AttributeError:
            log.error(
                f"{self._func_name} was not defined in a static module, cannot run in "
                "subprocess!"
            )

    def _check_run_in_container(self):
        if self._always_in_container:
            return True

        if "VEER_SINGULARITY" in os.environ:
            return True

        if "VEER_CONTAINER_IMAGE" in os.environ and "VEER_CONTAINER_APP" in os.environ:
            return True

    def _client(self, address_tpl):
        socket = self._setup_socket_client(address_tpl)
        args, kwargs = self._recv_arguments(socket)

        return_value = None
        try:
            return_value = self._func(*args, **kwargs)
        except Exception:
            wrapped = RemoteError()
            wrapped.wrap_exception()
            # send etxception
            self._send_returnvalue(socket, wrapped)
        finally:
            self._send_returnvalue(socket, return_value)

    def _get_container_args(self, script_filename):
        if self._container_image is None:
            container = get_config("default_container.image")
        else:
            container = self._container_image

        if container is None:
            raise IOError("No container image specified!")

        if not osp.isfile(container):
            raise IOError(f"Container image path does not exist: {container}")

        if self._container_app is None:
            app = get_config("default_container.app")
        else:
            app = self._container_app

        return [
            self._get_container_binary(),
            "exec",
            "--app",
            app,
            "-B",
            self._func_dir,
            container,
            get_config("python.binary"),
            script_filename,
        ]

    def _get_container_binary(self):
        from_config = get_config("singularity.binary")

        in_system = ds.find_executable(from_config)

        if in_system is None:
            raise OSError(f"Could not find singularity executable: {from_config}")
        return in_system

    def _get_func_dir(self, module_name):
        """Get the toplevel-directory of the module so that the import works in
        the submodule."""
        module = sys.modules[module_name]
        module_path = osp.abspath(module.__file__)

        if module_name == "__main__":
            return osp.dirname(module_path)

        base_module_name = module_name.split(".")[0]
        module_path_split = module_path.split(osp.sep)

        # adjust so osp.join creates an absolute path
        module_path_split[0] = "/"

        # find out where the base_module_folder is residing
        for i_end, folder in enumerate(module_path_split):
            if folder == base_module_name:
                break
        func_dir = osp.join(*module_path_split[:i_end])
        if not osp.isdir(func_dir):
            log.debug(f"func_dir: {func_dir} is no directory, shortening…")
            func_dir = osp.dirname(func_dir)
        log.debug(f"func_dir: {func_dir}")
        return func_dir

    def _get_module_import_name(self):
        if self._func_module != "__main__":
            return self._func_module
        else:
            module_path = osp.abspath(sys.modules[self._func_module].__file__)
            module_path = osp.basename(module_path)
            return osp.splitext(module_path)[0]

    def _host(self, *args, **kwargs):
        script_filename = None
        return_values = None
        process = None
        try:
            socket, address, port = self._setup_socket_host()
            script_filename = self._setup_script_file(address, port)

            # allow a single connection only
            socket.listen(1)

            process = self._spawn_process(script_filename)

            conn, client_address = socket.accept()

            self._send_arguments(conn, args, kwargs)
            return_values = self._recv_returnvalue(conn)

            process.wait()
        finally:
            if process is not None and process.poll() is None:
                process.kill()
            if script_filename is not None:
                util.delete_script_file(script_filename)
            socket.close()

        return return_values

    def _recv_arguments(self, socket):
        log.debug("Receiving arguments.")
        args, kwargs = util.recv_object(socket)
        return args, kwargs

    def _recv_returnvalue(self, socket):
        log.debug("Receiving return value.")
        retval = util.recv_object(socket)

        if isinstance(retval, RemoteError):
            # make sure the remote information is available to the host
            retval.write_to_log()

            # reraise the error here so that the userscript fails
            raise retval

        return retval

    def _send_arguments(self, socket, args, kwargs):
        log.debug("Sending arguments.")
        util.send_object(socket, (args, kwargs))

    def _send_returnvalue(self, socket, retval):
        log.debug("Sending return value.")
        util.send_object(socket, retval)

    def _setup_script_file(self, address, port):
        script = tempfile.NamedTemporaryFile(
            prefix="veer_", suffix=".py", mode="w", delete=False
        )
        log.debug(f"Setting up temporary script (filename: {script.name}).")

        # write preamble
        script.write(f"#!{sys.executable}\n")
        script.write("# encoding: utf-8\n")
        script.write("import sys, os\n")
        script.write("sys.path.append(os.getcwd())\n")

        # import the needed module
        script.write(f"import {self._get_module_import_name()} as target_module\n")

        # execute the client subfunction with the passed address
        script.write(
            f"target_module.{self._func_name}._client(('{address}', {port}))\n"
        )

        script.close()

        # delete temporary script file when the script exits
        atexit.register(util.delete_script_file, script.name)

        return script.name

    def _setup_socket_client(self, address_tpl):
        log.debug("Setting up client socket..")

        socket = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
        socket.connect(address_tpl)

        return socket

    def _setup_socket_host(self):
        socket = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
        socket.bind(("localhost", 0))
        address, port = socket.getsockname()
        if log.getEffectiveLevel() <= logging.DEBUG:
            log.debug(f"Set up host socket on {address}:{port}.")
        return socket, address, port

    def _spawn_process(self, script_filename):
        if self._check_run_in_container():
            log.debug("Spawning subprocess in container..")
            args = self._get_container_args(script_filename)
        else:
            log.debug("Spawning in subprocess..")
            args = [sys.executable, script_filename]

        return sp.Popen(args, cwd=self._func_dir, env={"VEER_PARENT": str(os.getpid())})
