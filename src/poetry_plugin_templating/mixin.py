from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from typing import IO as IOType
from typing import Any, BinaryIO, Callable, Optional, TextIO, cast

from poetry.core.masonry.builder import Builder

from poetry_plugin_templating.engine import TemplatingEngine


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
    src: IOType = open_mixin.original(path, *args, **kwargs)
    engine = TemplatingEngine(None, None)  # type: ignore

    if src.mode == "r":
        text_io: TextIO = cast(TextIO, src)
        processed = engine.process(text_io.read())
        return StringIO(processed)
    if src.mode == "rb":
        binary_io: BinaryIO = cast(BinaryIO, src)
        processed = engine.process(binary_io.read().decode("utf-8"))
        return BytesIO(processed.encode("utf-8"))
    return src


@Mixin.mixin(Builder, "build")
def builder_mixin(*args, **kwargs):
    with open_mixin:  # Replace Path.open method for duration of the build
        return builder_mixin.original(*args, **kwargs)
