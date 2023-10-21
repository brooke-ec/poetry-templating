from __future__ import annotations

import logging
import os
from io import BytesIO, StringIO
from pathlib import Path
from typing import IO as IOType
from typing import Any, BinaryIO, Callable, Optional, TextIO, cast

from poetry.core.masonry.builder import Builder
from poetry.core.pyproject.toml import PyProjectTOML

from poetry_plugin_templating.engine import TemplatingEngine

CONFIG_TABLE = "poetry_templating"

DEFAULT_ENCODING = "utf-8"
DEFAULT_INCLUDE = ["**/*.py"]
DEFAULT_EXCLUDE = []

_log = logging.getLogger(__name__)


class Mixin:
    """Represents a replacement action for an attribute of an object."""

    def __init__(self, obj: object, name: str, repl: Any) -> None:
        """Represents a replacement action for an attribute of an object.

        Parameters
        ----------
        obj : object
            The object the attribute belongs to.
        name : str
            The name of the attribute to replace.
        repl : Any
            The replacement.
        """
        self.replacement: Any = repl
        self.original: Any = None
        self.obj: object = obj
        self.name: str = name

    def __enter__(self) -> None:
        self.inject()

    def __exit__(self, *_) -> None:
        self.restore()

    def inject(self) -> None:
        """Inject the replacement into the object's attribute."""
        self.original = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.replacement)

    def restore(self) -> None:
        """Restore the attribute back to its original value"""
        setattr(self.obj, self.name, self.original)

    @staticmethod
    def mixin(
        obj: object, name: Optional[str] = None
    ) -> Callable[[Callable[..., Any]], Mixin]:
        """Decorator to generate a mixin from a function.

        Parameters
        ----------
        obj : object
            The object the attribute belongs to.
        name : str, optional
            The name of the attribute to replace, the name of the fucntion by default.
        """

        def wrapper(func: Callable[..., Any]) -> Mixin:
            return Mixin(obj, name or func.__name__, func)

        return wrapper


def get_configuration(pyproject: PyProjectTOML) -> dict:
    """Get the poetry templating configuration dictionary.

    Parameters
    ----------
    pyproject : PyProjectTOML
        The pyproject.toml file which contains the configuration.

    Returns
    -------
    dict
        The dictionary containing the poetry templating configuration.
    """
    tool_table = pyproject.data.get("tool")
    if not isinstance(tool_table, dict):
        raise TypeError("Could not find table 'tool'")

    config_table = tool_table.get(CONFIG_TABLE, {})
    if not isinstance(config_table, dict):
        raise TypeError(f"Could not find table 'tool.{CONFIG_TABLE}'")

    return config_table


def get_listable(table: dict, key: str, default: list = []) -> list:
    """Gets a list from the specified table and key. If the value is not a list, it will be wrapped in one.

    Parameters
    ----------
    table : dict
        The dictionary in which the desired key resides.
    key : str
        The key of the value to get.
    default : list, optional
        The default value to return if the key is not found. Empty list by default.

    Returns
    -------
    list
        The value in list form.
    """
    value = table.get(key, default)
    if not isinstance(value, list):
        value = [value]
    return value


def matches_any(path: Path, patterns: list[str]) -> bool:
    """Checks if the specified path matches any of the provided patterns.

    Parameters
    ----------
    path : Path
        The path to check against.
    patterns : list[str]
        A list of glob patterns to check against the path.

    Returns
    -------
    bool
        True if any of the patterns matched against the path.
    """
    normalized = Path(path.as_posix().lower())
    return any(normalized.match(p.lower().strip("/")) for p in patterns)


def get_relative(path: Path, root: str) -> Path:
    """Attempts to generate a relative path from the provided root. An absolute path will be returned if `path` is not a subpath of `root`.

    Parameters
    ----------
    path : Path
        The path to attempt to make relative.
    root : str
        The root directory to make the path relative to.

    Returns
    -------
    Path
        The resolved, relative path.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(root)
    except ValueError:
        return resolved


@Mixin.mixin(Builder, "build")
def builder_mixin(builder: Builder, *args, **kwargs):
    """Mixin to be injected into the Builder.build method to set up the templating system."""

    _log.debug("Setting up templating...")

    # Set up constants
    pyproject = builder._poetry.pyproject
    root, _ = os.path.split(pyproject.path)
    engine = TemplatingEngine(pyproject)

    # Get configuration
    configuration = get_configuration(pyproject)
    encoding = configuration.get("encoding", DEFAULT_ENCODING)
    include = get_listable(configuration, "include", DEFAULT_INCLUDE)
    exclude = get_listable(configuration, "exclude", DEFAULT_EXCLUDE)

    # Define replacement for Path.open method
    @Mixin.mixin(Path, "open")
    def open_mixin(path: Path, *args, **kwargs) -> IOType:
        src: IOType = open_mixin.original(path, *args, **kwargs)

        # Check if file in include list and not in exclude list
        rel = get_relative(path, root)
        if not matches_any(rel, include) or matches_any(rel, exclude):
            return src

        # Process file, considering if it was opened in binary mode
        if src.mode == "r":
            _log.debug("Templating engine processing '%s'", rel)
            text_io: TextIO = cast(TextIO, src)
            processed = engine.process(text_io.read())
            return StringIO(processed)
        if src.mode == "rb":
            _log.debug("Templating engine processing '%s'", rel)
            binary_io: BinaryIO = cast(BinaryIO, src)
            text = binary_io.read().decode(encoding)
            processed = engine.process(text).encode(encoding)
            return BytesIO(processed)
        return src  # Do not process files opened with write capabilities

    with open_mixin:  # Inject mixin for duration of the build
        return builder_mixin.original(builder, *args, **kwargs)
