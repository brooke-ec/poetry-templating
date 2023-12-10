import os
import tempfile

import pytest

BASIC_PYPROJECT_TOML = """
[tool.poetry]
name = "example_pyproject"
version = "1.2.3"
description = "Example description"
authors = []
license = "MIT"

[tool.poetry.dependencies]
python = "^3.8"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""


@pytest.fixture
def temp_file():
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w+") as f:
            yield f, path
    finally:
        os.remove(path)


@pytest.fixture
def pyproject_path(temp_file):
    f, path = temp_file

    f.write(BASIC_PYPROJECT_TOML)
    f.flush()

    yield path
