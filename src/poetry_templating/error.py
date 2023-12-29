from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from poetry_templating.engine import EvaluationContext


class TemplatingError(Exception):
    ...


class EvaluationError(TemplatingError):
    def __init__(self, ctx: "EvaluationContext", message) -> None:
        super().__init__(
            f"Error evaluating template: {message}\n  "
            + (
                f"Line {ctx.line}"
                if ctx.location is None
                else f'File "{ctx.location}", line {ctx.line}'
            )
        )
