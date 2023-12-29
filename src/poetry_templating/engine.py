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
RE_DELETE = re.compile(r"#\s*templating: delete", re.IGNORECASE)

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

        # Get configuration
        configuration = get_configuration(pyproject)
        self.encoding = configuration.get("encoding", DEFAULT_ENCODING)
        self.include = get_listable(configuration, "include", DEFAULT_INCLUDE)
        self.exclude = get_listable(configuration, "exclude", DEFAULT_EXCLUDE)

    def relative(self, path: StrPath) -> Path:
        return relative(path, self.root)

    def should_process(self, path: StrPath) -> bool:
        rel = relative(path, self.root)
        return matches_any(rel, self.include) and not matches_any(rel, self.exclude)

    def evaluate_and_replace(self) -> int:
        count = 0
        for path in (os.path.join(p, f) for p, _, fs in os.walk(self.root) for f in fs):
            if self.should_process(path):
                count += 1
                result = ""
                ctx = EvaluationContext(path, self)
                with open(path, "r+") as file:
                    for line in file:
                        evaluated = ctx.evaluate_line(line)
                        if evaluated is not None:
                            result += evaluated
                    file.seek(0)
                    file.write(result)
                    file.truncate()

        return count

    def evaluate_string(
        self,
        data: str,
        location: Optional[StrPath] = None,
    ) -> str:
        result: List[str] = []
        ctx = EvaluationContext(location, self)
        for line in data.split("\n"):
            evaluated = ctx.evaluate_line(line)
            if evaluated is not None:
                result.append(evaluated)
        return "\n".join(result)


class EvaluationContext:
    def __init__(
        self,
        location: Optional[StrPath],
        engine: TemplatingEngine,
    ) -> None:
        self.location = location and engine.relative(location)
        self.engine = engine
        self.enabled = True
        self.line = -1

    def evaluate_line(self, data: str) -> Union[str, None]:
        self.line += 1

        # Check for on/off comment
        if RE_DISABLE.match(data):
            self.enabled = False
            return None
        if RE_ENABLE.match(data):
            self.enabled = True
            return None

        # Process line
        if self.enabled:
            # Skip if ends with delete comment
            if RE_DELETE.search(data):
                return None

            return self.evaluate_string(data)
        else:
            return data

    def evaluate_string(self, data: str) -> str:
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
        raise EvaluationError(self, "Unknown Construct")


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
        pattern: Union[Pattern, str],
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
        if ctx.location is None:
            raise EvaluationError(ctx, "Relative paths are not permitted in this context")
        path = os.path.join(ctx.engine.root, os.path.dirname(ctx.location), path)

    if not os.path.isfile(path):
        raise EvaluationError(ctx, f'No such file "{os.path.abspath(path)}"')

    with open(path, "r", encoding=ctx.engine.encoding) as f:
        content = f.read()
        if ctx.engine.should_process(path):
            content = ctx.engine.evaluate_string(content, path)
        return content


@Construct.construct(r"^env(?:\.([^\.\s]+))?$")
def environ_construct(match: Match, ctx: EvaluationContext) -> str:
    key = match.group(1)

    if key is None:
        return str(dict(os.environ))

    if key not in os.environ:
        raise EvaluationError(ctx, f"No environment variable '{key}'")

    return os.environ[key]


if __name__ == "__main__":
    pyproject = PyProjectTOML(Path("pyproject.toml"))
    engine = TemplatingEngine(pyproject)

    result = engine.evaluate_string("${pyproject.tool.poetry.authors}")
    print(result)
