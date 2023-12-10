import os
from pathlib import Path

import pytest
from poetry.core.pyproject.toml import PyProjectTOML
from poetry_templating.util import (
    Mixin,
    get_configuration,
    get_listable,
    matches_any,
    relative,
    traverse,
)

# test mixins


@pytest.fixture
def mixin_pair():
    class TestMixinTarget:
        def test(self) -> bool:
            return False

    @Mixin.mixin(TestMixinTarget, "test")
    def mixin(self) -> bool:
        return True

    return TestMixinTarget, mixin


def test_mixin_inject(mixin_pair):
    instance = mixin_pair[0]()

    # ensure not injected
    assert not instance.test()

    # inject and ensure injected
    mixin_pair[1].inject()
    assert instance.test()


def test_mixin_restore(mixin_pair):
    instance = mixin_pair[0]()
    mixin_pair[1].inject()
    mixin_pair[1].restore()
    assert not instance.test()


def test_mixin_context(mixin_pair):
    instance = mixin_pair[0]()
    assert not instance.test()

    with mixin_pair[1]:
        assert instance.test()

    assert not instance.test()


# test matches_any


@pytest.mark.parametrize(
    "path, patterns",
    [
        ("src/test.py", ["*.py"]),
        ("test.py", ["*.png", "test.py"]),
        ("src/test.PY", ["*.py"]),
        ("src/test.py", ["/*.py"]),
        pytest.param(
            "src\\test.py",
            ["src/test.py"],
            marks=pytest.mark.skipif(os.name != "nt", reason="posix"),
        ),
    ],
)
def test_glob_matches(path, patterns):
    assert matches_any(path, patterns)


@pytest.mark.parametrize(
    "path, patterns",
    [
        ("src/test.pyi", ["*.py"]),
        ("not_test.py", ["test.py"]),
    ],
)
def test_glob_not_matches(path, patterns):
    assert not matches_any(path, patterns)


@pytest.mark.parametrize("dictionary", [{"key": "success"}, {"key": ["success"]}, {}])
def test_get_listable(dictionary):
    assert get_listable(dictionary, "key", ["success"]) == ["success"]


# test traverse


@pytest.fixture
def demo_structure():
    return {"list": [{"name": 1}, 2], "dict": {"subdict": 3}, "top": 4}


@pytest.mark.parametrize(
    "path, expected",
    [
        ("list.0.name", 1),
        ("list.1", 2),
        ("dict.subdict", 3),
        ("top", 4),
        ("dict", {"subdict": 3}),
    ],
)
def test_traverse(path, expected, demo_structure):
    assert traverse(demo_structure, path) == expected


@pytest.mark.parametrize(
    "path, error",
    [
        ("unknown", KeyError),
        ("list.a", ValueError),
        ("list.2", IndexError),
        ("top.sub", ValueError),
    ],
)
def test_traverse_errors(path, error, demo_structure):
    try:
        traverse(demo_structure, path)
    except Exception as e:
        assert isinstance(e, error)
    else:
        assert False


# test get_configuration


def test_get_configuration_present(pyproject_path):
    with open(pyproject_path, "a") as f:
        f.write("\n[tool.poetry-templating]\nsuccessful = true")
        f.flush()

    pyproject = PyProjectTOML(Path(pyproject_path))
    assert get_configuration(pyproject) == {"successful": True}


def test_get_configuration_missing(pyproject_path):
    pyproject = PyProjectTOML(Path(pyproject_path))
    assert get_configuration(pyproject) == {}


def test_get_configuration_missing_tool(temp_file):
    pyproject = PyProjectTOML(Path(temp_file[1]))

    try:
        get_configuration(pyproject)
    except Exception as e:
        assert isinstance(e, TypeError)
    else:
        assert False


def test_get_configuration_type_mismatch(pyproject_path):
    with open(pyproject_path, "a") as f:
        f.write("\n[tool]\npoetry-templating = true")
        f.flush()

    pyproject = PyProjectTOML(Path(pyproject_path))
    try:
        get_configuration(pyproject)
    except Exception as e:
        assert isinstance(e, TypeError)
    else:
        assert False


# test relative


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/top/root/subdir", "subdir"),
        ("/top/root/../root/subdir", "subdir"),
    ],
)
def test_relative(path, expected):
    root = Path("/top/root").resolve()
    assert relative(path, root) == Path(expected).resolve()


def test_relative_absolute():
    root = Path("/top/root").resolve()
    expected = Path("/diff/root").resolve()
    assert relative(expected, root) == expected
