from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, Callable, Optional

from cleo.io.io import IO
from poetry.core.masonry.builders.wheel import WheelBuilder

from poetry_plugin_templating.engine import TemplatingEngine


class Mixin:
    def __init__(self, obj: object, name: str, repl: Any) -> None:
        self.obj: object = obj
        self.name: str = name
        self.repl: Any = repl
        self.orig: Any = None

    def __enter__(self):
        self.orig = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.repl)

    def __exit__(self, *_):
        setattr(self.obj, self.name, self.orig)

    @staticmethod
    def new(
        obj: object, name: Optional[str] = None
    ) -> Callable[[Callable[..., Any]], Mixin]:
        def wrapper(func: Callable[..., Any]) -> Mixin:
            return Mixin(obj, name or func.__name__, func)

        return wrapper
