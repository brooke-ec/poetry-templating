from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from poetry_plugin_templating.engine import TemplatingReader


class Mixin:
    def __init__(self, obj: object, name: str, repl: Any) -> None:
        self.replacement: Any = repl
        self.original: Any = None
        self.obj: object = obj
        self.name: str = name

    def __enter__(self) -> None:
        self.inject()

    def __exit__(self, *_) -> None:
        self.restore()

    def inject(self) -> None:
        self.original = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.replacement)

    def restore(self) -> None:
        setattr(self.obj, self.name, self.original)

    @staticmethod
    def mixin(
        obj: object, name: Optional[str] = None
    ) -> Callable[[Callable[..., Any]], Mixin]:
        def wrapper(func: Callable[..., Any]) -> Mixin:
            return Mixin(obj, name or func.__name__, func)

        return wrapper


@Mixin.mixin(Path, "open")
def open_mixin(path: Path, *args, **kwargs):
    src = open_mixin.original(path, *args, **kwargs)
    reader = TemplatingReader(None, src)  # type: ignore
    return reader
