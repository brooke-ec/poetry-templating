import logging
import os
import re
from typing import Optional

from poetry.core.pyproject.toml import PyProjectTOML

from poetry_plugin_templating import DEFAULT_ENCODING, DEFAULT_EXCLUDE, DEFAULT_INCLUDE
from poetry_plugin_templating.util import (
    StrPath,
    get_configuration,
    get_listable,
    get_relative,
    matches_any,
)

RE_TEMPLATE_SLOT = re.compile(r"(?:#\s*)?\${(.+)}")

_log = logging.getLogger(__name__)


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
        self.root = os.path.dirname(pyproject.path)
        self.cache: dict[str, str] = {}

        # Get configuration
        configuration = get_configuration(pyproject)
        self.encoding = configuration.get("encoding", DEFAULT_ENCODING)
        self.include = get_listable(configuration, "include", DEFAULT_INCLUDE)
        self.exclude = get_listable(configuration, "exclude", DEFAULT_EXCLUDE)

    def should_process(self, path: StrPath) -> bool:
        rel = get_relative(path, self.root)
        return matches_any(rel, self.include) or matches_any(rel, self.exclude)

    def process(self, data: str, path: Optional[StrPath] = None) -> str:
        """Process the provided data, substituting template slots with their resolved values.

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
            path = get_relative(path, self.root)
            _log.debug("Templating Engine Processing '%s'", path.as_posix())

        data = RE_TEMPLATE_SLOT.sub("TEMPLATED!!!", data)
        return data
