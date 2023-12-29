import os
import tempfile

import pytest

BASIC_PYPROJECT_TOML = """
[tool.poetry]
name = "example"
packages = [{include="example"}]
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


@pytest.fixture
def project_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
            f.write(BASIC_PYPROJECT_TOML)

        os.mkdir(os.path.join(tmpdir, "example"))
        with open(os.path.join(tmpdir, "example", "__init__.py"), "w") as f:
            f.write("${'Success!'}")
        yield tmpdir
