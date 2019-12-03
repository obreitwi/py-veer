# py-veer
Seamless execution of Python code in different environments, be it simple
sub-processes or singularity containers.


## `veer.in_subprocess`

Run a function in a subprocess with a single decorator.

```python
import os
import veer

@veer.in_subprocess
def foobar(arg1, arg2, kwarg="default"):
    result = f"I run in PID: {os.getpid()}"
    return result


if __name__ == "__main__":
    print(f"Main process runningin PID {os.getpid()}")
    print(foobar())
```

The wrapped function will be executed in a new instance receiving its argument
pickled via TCP streams. The return values are transferred by to the main
process the same way. Hence, the wrapped function should not have any data
dependencies except for its arguments and return values as it will be excecuted
in a fresh interpreter instance.

*NOTE:* This decorator *REQUIRES* you to encapsulate your python scripts with a
check for `__main__` in `__name__`, otherwise your code might be executed twice
if you decorate a function from the main file.


## `veer.in_container`

Run a function in a different singularity container and app.

```python
import os
import subprocess
import veer

@veer.in_container(image="container.img",
                   app="special-environment")
def foobar():
    return subprocess.check_output(["lsb_release", "-a"]).decode("utf-8")


if __name__ == "__main__":
    print("Main process:")
    print(subprocess.check_output(["lsb_release", "-a"]).decode("utf-8"))
    print("Child process:")
    print(foobar())
```

This works almost like `veer.in_subprocess` but allows for easy switching of
environments.

## Environmental setings

If `VEER_SINGULARITY` is defined or `VEER_CONTAINER_IMAGE` and
`VEER_CONTAINER_APP` are defined, the functions decorated by
`veer.in_subprocess` are run in the specified (or the default) singularity
container.


## Configuration

Configuration can be used to set the path to binaries for
`python`/`singularity` as well as to define a default container image/app.
They can be interactively via `veer.set_config("singularity.binary", PATH)` or
via YAML/JSON files that are looked for in the following locations:

* environment variable `${VEER_CONFIG}` pointing to the exact file
* `${PWD}/veer/config.{yaml,json}`
* `${XDG_CONFIG_HOME}/veer/config.{yaml,json}`
* `${XDG_CONFIG_DIRS}/veer/config.{yaml,json}`

An example:
```yaml
singularity:
  binary: singularity
python:
  binary: python

default_container:
  image: /path/to/container.sif
  app: my-default-app
```


## Tests

Tests can be executed after install via `(cd tests && nosetests --verbose .)`.
Some tests require a singularity test containre that can be build via:
```console
# singularity build tests/veer_test_container.sif tests/veer_test_container.def
```


## Requirements

* Python 3.7+
* [pbr](https://pypi.org/project/pbr/)
