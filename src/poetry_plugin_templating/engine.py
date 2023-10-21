import re
from typing import IO as IOType
from typing import Any

from cleo.io.io import IO
from poetry.core.pyproject.toml import PyProjectTOML

RE_TEMPLATE_SLOT = re.compile(r"(?<!!)\${([\w.]+)}")
RE_ESCAPED_SLOT = re.compile(r"!(?=\${([\w.]+)})")


class TemplatingEngine:
    def __init__(self, io: IO, pyproject: PyProjectTOML) -> None:
        self.pyproject: PyProjectTOML = pyproject
        self.io: IO = io

    def process(self, data: str) -> str:
        data = RE_TEMPLATE_SLOT.sub("TEMPLATED!", data)
        data = RE_ESCAPED_SLOT.sub("", data)
        return data


class TemplatingReader(IOType):
    def __init__(self, engine: TemplatingEngine, source: IOType) -> None:
        super().__init__()
        self.engine = engine
        self.source = source

    # Redirect Unknown Attributes
    def __getattribute__(self, name: str) -> Any:
        if (
            name in super().__getattribute__("__dict__")
            or name in TemplatingReader.__dict__
        ):
            return super().__getattribute__(name)
        else:
            return getattr(super().__getattribute__("source"), name)

    # Override because with doesn't call __getattribute__
    def __enter__(self) -> IOType:
        self.source.__enter__()
        return self

    # Override because with doesn't call __getattribute__
    def __exit__(self, *args, **kwargs):
        return self.source.__exit__(*args, **kwargs)
