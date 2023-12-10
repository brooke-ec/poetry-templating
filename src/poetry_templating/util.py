from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from poetry.core.pyproject.toml import PyProjectTOML

from poetry_templating import CONFIG_TABLE

StrPath = Union[Path, str]


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


def matches_any(path: StrPath, patterns: list[str]) -> bool:
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
    normalized = Path(Path(path).as_posix().lower())
    return any(normalized.match(p.lower().strip("/")) for p in patterns)


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


def get_listable(dict: dict, key: str, default: list = []) -> list:
    """Gets a list from the specified dictionary and key. If the value is not a list, it will be wrapped in one.

    Parameters
    ----------
    dict : dict
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
    value = dict.get(key, default)
    if not isinstance(value, list):
        value = [value]
    return value


def relative(path: StrPath, root: str) -> Path:
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
    resolved = Path(os.path.realpath(path))
    try:
        return resolved.relative_to(root)
    except ValueError:
        return resolved


def traverse(
    structure: Union[Dict[str, Any], List[Any]],
    path: Union[str, List[str]],
) -> Any:
    """Gets value at the provided path from the given dictionary or list.

    Paths should be a list of keys/indexes as either a list or string, separated by dots.

    Parameters
    ----------
    structure : dict | list
        The structure to traverse through.
    path : str | list[str]
        The path to the value to return.

    Returns
    -------
    Any
        The value at the provided path

    Raises
    ------
    KeyError
        Raised when attempting to access a dictionary key that does not exist.
    ValueError
        Raised when an unexpected value is found while traversing.
    IndexError
        Raised when attempting to access a list item that does not exist.
    """
    if isinstance(path, str):
        path = path.split(".")

    current = structure
    for i, step in enumerate(path):
        if isinstance(current, dict):  # Handle dictionaries
            if step not in current:
                raise KeyError(f"{'.'.join(path[:i + 1])} does not exist")
            current = current[step]
        elif isinstance(current, list):  # Handle lists
            try:
                index = int(step)
            except ValueError:
                raise ValueError(f"'{step}' is not a valid list index")

            if index >= len(current):
                raise IndexError(
                    f"{index} is out of range for list at {'.'.join(path[:i])}"
                )

            current = current[index]
        else:
            raise ValueError(f"Expected list or dictionary at {'.'.join(path[:i])}")

    return current
