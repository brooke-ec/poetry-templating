import os
import re
import shutil
import sys
import tempfile
import time
from io import StringIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from cleo.io.inputs.argv_input import ArgvInput
from cleo.io.io import IO
from cleo.io.outputs.stream_output import StreamOutput
from poetry.console.application import Application
from poetry.console.application import Application as PoetryApplication
from poetry.console.commands.build import BuildCommand
from poetry.factory import Factory
from poetry.utils.env import EnvManager, VirtualEnv
from poetry_templating.plugin import EvaluateCommand, TemplatingPlugin, progress
from poetry_templating.util import Mixin


@pytest.fixture
def tmp_venv():
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir)
        EnvManager.build_venv(venv_path)
        venv = VirtualEnv(venv_path)

        yield venv

        shutil.rmtree(venv.path)


@pytest.fixture
def basic_io():
    return IO(ArgvInput([]), StreamOutput(sys.stdout), StreamOutput(sys.stderr))


def test_evaluate_command(project_path, basic_io):
    poetry = Factory().create_poetry(project_path)
    command = EvaluateCommand()
    command._poetry = poetry

    command.execute(basic_io)

    with open(os.path.join(project_path, "example", "__init__.py"), "r") as f:
        assert f.read() == "Success!"


def test_decorated_progress():
    buffer = StringIO()
    os.environ["NO_COLOR"] = "1"
    output = StreamOutput(buffer)
    io = IO(ArgvInput([]), output, output)
    os.environ.pop("NO_COLOR")

    io.decorated()
    with progress(io, "Testing..."):
        time.sleep(1)

    assert (
        re.search("\r\x1b\\[2KTesting... <debug>\\(\\d+\\.\\d+s\\)", buffer.getvalue())
        is not None
    )


def test_build_templating(project_path, basic_io, tmp_venv):
    poetry = Factory().create_poetry(project_path)
    command = BuildCommand()
    command._poetry = poetry
    command._env = tmp_venv

    plugin = TemplatingPlugin()
    plugin.root = Path(project_path)
    plugin.poetry = poetry

    basic_io.input._definition = command.definition

    plugin.setup_build(command)
    command.execute(basic_io)

    artefact = os.path.join(project_path, "dist", "example-1.2.3-py3-none-any.whl")
    with ZipFile(artefact).open("example/__init__.py") as f:
        assert f.read().decode("utf-8") == "Success!"


def test_help():
    buffer = StringIO()
    os.environ["NO_COLOR"] = "1"
    output = StreamOutput(buffer)
    os.environ.pop("NO_COLOR")
    application = PoetryApplication()
    application.auto_exits(False)
    application.run(ArgvInput(["", "help", "templating evaluate"]), output, output)

    expected = "Description:\n  " + EvaluateCommand.description
    assert buffer.getvalue().strip().startswith(expected)


def test_setup_build():
    executed = False

    @Mixin.mixin(TemplatingPlugin, "setup_build")
    def plugin_mixin(*args, **kwargs):
        nonlocal executed
        executed = True

    @Mixin.mixin(BuildCommand, "handle")
    def command_mixin(*args, **kwargs):
        return

    with plugin_mixin, command_mixin:
        application = PoetryApplication()
        application.auto_exits(False)
        application.run(ArgvInput(["", "build"]))

    assert executed


def test_no_pyproject(basic_io, tmp_venv):
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            TemplatingPlugin().activate(Application())
        except RuntimeError:
            raise
        except Exception:
            pass
        finally:
            os.chdir(old_cwd)
