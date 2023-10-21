import re

from poetry.core.pyproject.toml import PyProjectTOML

RE_TEMPLATE_SLOT = re.compile(r"(?<!!)\${([\w.]+)}")
RE_ESCAPED_SLOT = re.compile(r"!(?=\${([\w.]+)})")


class TemplatingEngine:
    """The Templating Engine class is responsible for processing strings and substituting template slots with their resolved values."""

    def __init__(self, pyproject: PyProjectTOML) -> None:
        """The Templating Engine class is responsible for processing strings and substituting template slots with their resolved values.

        Parameters
        ----------
        pyproject : PyProjectTOML
            The pyproject.toml of the parent package.
        """
        self.pyproject: PyProjectTOML = pyproject

    def process(self, data: str) -> str:
        """Process the provided data, substituting template slots with their resolved values.

        Parameters
        ----------
        data : str
            The data to process.

        Returns
        -------
        str
            The processed data.
        """

        data = RE_TEMPLATE_SLOT.sub("TEMPLATED!", data)
        data = RE_ESCAPED_SLOT.sub("", data)
        return data
