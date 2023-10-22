from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from re import Match, Pattern
from typing import Callable, List, Optional, Union

from poetry.core.pyproject.toml import PyProjectTOML

from poetry_templating import DEFAULT_ENCODING, DEFAULT_EXCLUDE, DEFAULT_INCLUDE
from poetry_templating.error import EvaluationError
from poetry_templating.util import (
    StrPath,
    get_configuration,
    get_listable,
    matches_any,
    relative,
    traverse,
)

RE_TEMPLATE_SLOT = re.compile(r"(?:#\s*)?\${(.+)}")

RE_DISABLE = re.compile(r"^\s*#\s*templating: off\s*$", re.IGNORECASE)
RE_ENABLE = re.compile(r"^\s*#\s*templating: on\s*$", re.IGNORECASE)

_log = logging.getLogger(__name__)


class TemplatingEngine:
    """The Templating Engine class is responsible for processing strings and substituting template slots with their evaluated values."""

    def __init__(self, pyproject: PyProjectTOML) -> None:
        """The Templating Engine class is responsible for processing strings and substituting template slots with their evaluated values.

        Parameters
        ----------
        pyproject : PyProjectTOML
            The pyproject.toml of the parent package.
        """
        self.pyproject: PyProjectTOML = pyproject
        self.root = os.path.dirname(pyproject.path)
        self.cache: dict[Path, str] = {}

        # Get configuration
        configuration = get_configuration(pyproject)
        self.encoding = configuration.get("encoding", DEFAULT_ENCODING)
        self.include = get_listable(configuration, "include", DEFAULT_INCLUDE)
        self.exclude = get_listable(configuration, "exclude", DEFAULT_EXCLUDE)

    def should_process(self, path: StrPath) -> bool:
        rel = relative(path, self.root)
        return matches_any(rel, self.include) and not matches_any(rel, self.exclude)

    def evaluate_file(self, data: str, path: Optional[StrPath] = None) -> str:
        """Process the provided data, substituting template slots with their evaluated values.

        Parameters
        ----------
        data : str
            The data to process.
        path : Union[Path, str], optional
            The path to the file that is being processed.

        Returns
        -------
        str
            The processed data.
        """
        if path is not None:
            path = self.relative(path)
            _log.debug("Templating Engine Processing '%s'", path.as_posix())

            # Cancel if file shouldn't be processed
            if not self.should_process(path):
                return data

            # Check if file is in cache
            if path in self.cache:
                return self.cache[path]

        # Process one line at a time
        enabled = True
        lines: List[str] = []
        ctx = EvaluationContext(0, path, self)
        for line in data.split("\n"):
            ctx.line += 1

            # Check for on/off comment
            if RE_DISABLE.match(line):
                enabled = False
                continue
            if RE_ENABLE.match(line):
                enabled = True
                continue

            # Process line
            if enabled:
                lines.append(ctx.evaluate_string(line))
            else:
                lines.append(line)

        result = "\n".join(lines)

        # Add to cache
        if path is not None:
            self.cache[path] = result
        return result

    def relative(self, path: StrPath) -> Path:
        return relative(path, self.root)


class EvaluationContext:
    def __init__(
        self,
        line: int,
        path: Optional[StrPath],
        engine: TemplatingEngine,
    ) -> None:
        self.engine = engine
        self.path = path
        self.line = line

    def evaluate_string(self, data: str):
        return RE_TEMPLATE_SLOT.sub(self._evaluate_slot, data)

    def _evaluate_slot(self, match: re.Match) -> str:
        content = match.group(1)
        for construct in Construct.constructs:
            check = construct.pattern.match(content)
            if check is not None:
                try:
                    return construct.handler(check, self)
                except Exception as e:
                    if isinstance(e, EvaluationError):
                        raise
                    raise EvaluationError(self, e) from e
        raise EvaluationError(self, "Invalid Syntax")


class Construct:
    constructs: List["Construct"] = []

    def __init__(
        self,
        pattern: Pattern,
        handler: Callable[[Match, EvaluationContext], str],
    ) -> None:
        Construct.constructs.append(self)
        self.handler = handler
        self.pattern = pattern

    @staticmethod
    def construct(
        pattern: Union[Pattern, str]
    ) -> Callable[[Callable[[Match, EvaluationContext], str]], Construct]:
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        def wrapper(func: Callable[[Match, EvaluationContext], str]) -> Construct:
            return Construct(pattern, func)

        return wrapper


# Define Constructs


@Construct.construct("^[\"'](.+)[\"']$")
def literal_construct(match: Match, ctx: EvaluationContext) -> str:
    return ctx.evaluate_string(match.group(1))


@Construct.construct(r"^pyproject((?:\.[^.]+)+)?$")
def pyproject_construct(match: Match, ctx: EvaluationContext) -> str:
    path = match.group(1)

    if path is None:
        return str(ctx.engine.pyproject.data)

    result = traverse(ctx.engine.pyproject.data, path[1:])
    return str(result)


@Construct.construct(r"^(\.?(?:\/.+)+)$")
def file_construct(match: Match, ctx: EvaluationContext) -> str:
    path: str = match.group(1)

    if path.startswith("/"):
        path = os.path.join(ctx.engine.root, path[1:])
    else:
        if ctx.path is None:
            raise EvaluationError(ctx, "Relative paths are not permitted in this context")
        path = os.path.join(ctx.engine.root, os.path.dirname(ctx.path), path)

    if not os.path.isfile(path):
        raise EvaluationError(ctx, f'No such file "{os.path.abspath(path)}"')

    with open(path, "r", encoding=ctx.engine.encoding) as f:
        return ctx.engine.evaluate_file(f.read(), path)


@Construct.construct(r"^env(?:\.([^\.\s]+))?$")
def environ_construct(match: Match, ctx: EvaluationContext) -> str:
    key = match.group(1)

    if key is None:
        return str(dict(os.environ))

    if key not in os.environ:
        raise EvaluationError(ctx, f"No environment variable '{key}'")

    return os.environ[key]
