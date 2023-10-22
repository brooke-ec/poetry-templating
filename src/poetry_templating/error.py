import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poetry_templating.engine import EvaluationContext

_log = logging.getLogger(__name__)


class TemplatingError(Exception):
    def __init__(self, ctx: "EvaluationContext", message) -> None:
        super().__init__(
            f"Error evaluating template: {message} \n  "
            + (
                f"Line {ctx.line}"
                if ctx.path is None
                else f'File "{ctx.path}", line {ctx.line}'
            )
        )
