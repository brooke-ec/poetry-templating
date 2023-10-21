import re

from poetry.core.pyproject.toml import PyProjectTOML

RE_TEMPLATE_SLOT = re.compile(r"(?<!!)\${([\w.]+)}")
RE_ESCAPED_SLOT = re.compile(r"!(?=\${([\w.]+)})")


class TemplatingEngine:
    def __init__(self, pyproject: PyProjectTOML) -> None:
        self.pyproject: PyProjectTOML = pyproject

    def process(self, data: str) -> str:
        data = RE_TEMPLATE_SLOT.sub("TEMPLATED!", data)
        data = RE_ESCAPED_SLOT.sub("", data)
        return data
