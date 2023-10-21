import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poetry_plugin_templating.engine import EvaluationContext

_log = logging.getLogger(__name__)


class TemplatingError(Exception):
    def __init__(self, ctx: "EvaluationContext", message) -> None:
        super().__init__(
            f"""Error evaluating template: {message}
    File "{ctx.path}", line {ctx.line}"""
        )
