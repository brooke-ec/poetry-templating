import pytest
from poetry_templating.util import Mixin, get_listable, matches_any


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


@pytest.mark.parametrize(
    "path, patterns",
    [
        ("src/test.py", ["*.py"]),
        ("test.py", ["*.png", "test.py"]),
        ("src/test.PY", ["*.py"]),
        ("src/test.py", ["/*.py"]),
        ("src\\test.py", ["src/test.py"]),
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
