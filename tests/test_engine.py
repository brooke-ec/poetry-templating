import os
import uuid
from pathlib import Path

import pytest
from poetry.core.pyproject.toml import PyProjectTOML
from poetry_templating.engine import TemplatingEngine
from poetry_templating.error import EvaluationError

from tests.conftest import BASIC_PYPROJECT_TOML


@pytest.fixture
def temp_engine(project_path):
    pyproject = PyProjectTOML(Path(project_path) / "pyproject.toml")
    return TemplatingEngine(pyproject)


def test_evaluate_and_replace(temp_engine):
    temp_engine.evaluate_and_replace()

    with open(os.path.join(temp_engine.root, "example", "__init__.py"), "r") as f:
        assert f.read() == "Success!"


@pytest.mark.parametrize(
    "include, exclude, path, result",
    [
        ('"*.py"', "[]", "test.py", True),
        ('"*.py"', '"test.py"', "test.py", False),
        ('"test.py"', '"test.py"', "test.py", False),
        ('"*.py"', "[]", "random.txt", False),
    ],
)
def test_should_process_inclusion(include, exclude, path, result, pyproject_path):
    with open(pyproject_path, "a") as f:
        f.write(
            f"""
[tool.poetry-templating]
include = {include}
exclude = {exclude}
"""
        )

    pyproject = PyProjectTOML(Path(pyproject_path))
    engine = TemplatingEngine(pyproject)

    assert engine.should_process(path) == result


def test_processed_status(temp_engine):
    assert temp_engine.should_process("test.py")
    temp_engine.set_processed("test.py")
    assert not temp_engine.set_processed("test.py")


def test_evaluate_string(temp_engine):
    result = temp_engine.evaluate_string("${'Success!'}")
    assert result == "Success!"


def test_line_disable(temp_engine):
    result = temp_engine.evaluate_string(
        """
# templating: off
example = "${'will NOT get evaluated'}"
# templating: on
evaluated = "${'WILL get evaluated'}"
"""
    )

    assert (
        result
        == """
example = "${'will NOT get evaluated'}"
evaluated = "WILL get evaluated"
"""
    )


def test_line_delete(temp_engine):
    assert temp_engine.evaluate_string("production = false # templating: delete") == ""


@pytest.mark.parametrize("symbol", ["'", '"'])
def test_literal_contruct(symbol, temp_engine):
    result = temp_engine.evaluate_string("${" + symbol + "Success!" + symbol + "}")
    assert result == "Success!"


def test_pyproject_construct_value(temp_engine):
    result = temp_engine.evaluate_string("${pyproject.tool.poetry.version}")
    assert result == "1.2.3"


def test_pyproject_construct_everything(temp_engine):
    result = temp_engine.evaluate_string("${pyproject}")
    assert result == str(temp_engine.pyproject.data)


def test_file_construct_absolute(temp_engine):
    result = temp_engine.evaluate_string("${/pyproject.toml}")
    assert result == BASIC_PYPROJECT_TOML


def test_file_construct_relative_fail(temp_engine):
    try:
        temp_engine.evaluate_string("${./pyproject.toml}")
    except EvaluationError:
        pass
    else:
        raise AssertionError("Expected exception was not raised.")


def test_file_construct_relative(temp_engine):
    location = os.path.join(temp_engine.root, "example", "test.py")
    result = temp_engine.evaluate_string("${./__init__.py}", location)
    assert result == "Success!"


def test_file_construct_not_found(temp_engine):
    try:
        temp_engine.evaluate_string("${/nonexistent.txt}")
    except EvaluationError:
        pass
    else:
        raise AssertionError("Expected exception was not raised.")


def test_environ_construct_everything(temp_engine):
    result = temp_engine.evaluate_string("${env}")
    assert result == str(dict(os.environ))


def test_environ_construct(temp_engine):
    k, v = uuid.uuid4().hex, uuid.uuid4().hex
    os.environ[k] = v
    try:
        result = temp_engine.evaluate_string("${env." + k + "}")
        assert result == v
    finally:
        os.environ.pop(k)


def test_environ_construct_fail(temp_engine):
    try:
        temp_engine.evaluate_string("${env.nonexistent}")
    except EvaluationError:
        pass
    else:
        raise AssertionError("Expected exception was not raised.")
