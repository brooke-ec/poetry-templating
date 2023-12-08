import logging
from io import BytesIO, StringIO
from os import stat_result
from pathlib import Path
from tarfile import TarFile, TarInfo
from typing import IO as IOType
from typing import Union, cast

from poetry.console.application import Application
from poetry.core.masonry.builder import Builder
from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_templating.error import TemplatingError
from poetry_templating.util import Mixin

_log = logging.getLogger(__name__)


class TemplatingPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        builder_mixin.inject()  # Inject builder mixin so that templating is setup when a build is started.


# Mixin to be injected into the Builder.build method to set up the templating system.
@Mixin.mixin(Builder, "build")
def builder_mixin(builder: Builder, *args, **kwargs):
    _log.debug("Setting up Templating System...")
    from poetry_templating.engine import TemplatingEngine

    # Set up templating engine
    engine = TemplatingEngine(builder._poetry.pyproject)

    # Define replacement for Path.open method
    @Mixin.mixin(Path, "open")
    def open_mixin(path: Path, mode: str = "r", *args, **kwargs) -> IOType:
        relative = engine.relative(path)
        in_cache = relative in engine.cache
        writable = mode not in ("r", "rb")

        try:
            if in_cache and not writable:
                evaluated = engine.cache[relative]
            else:
                src: IOType = open_mixin.original(path, mode, *args, **kwargs)
                if writable or not engine.should_process(path):
                    return src

                raw: Union[str, bytes] = src.read()
                if isinstance(raw, bytes):
                    raw = cast(bytes, raw).decode(engine.encoding)
                evaluated = engine.evaluate_file(raw, path)  # type: ignore

            # Process file, considering if it was opened in binary mode
            if mode == "r":
                return StringIO(evaluated)
            else:
                return BytesIO(evaluated.encode(engine.encoding))

        except Exception as e:
            if isinstance(e, TemplatingError):
                raise
            raise TemplatingError(
                f'Error processing template: {e}\n  File "{relative}"'
            ) from e

    # Define replacement for TarFile.gettarinfo method
    @Mixin.mixin(TarFile, "gettarinfo")
    def tar_info_mixin(tarfile, path, *args, **kwargs) -> TarInfo:
        info: TarInfo = tar_info_mixin.original(tarfile, path, *args, **kwargs)
        if engine.should_process(path):
            info.size = len(Path(path).read_bytes())
        return info

    # Define replacement for Path.stat method
    @Mixin.mixin(Path, "stat")
    def stat_mixin(path: Path):
        info: stat_result = stat_mixin.original(path)
        if engine.should_process(path):
            size = len(Path(path).read_bytes())
            info = stat_result(
                [
                    info.st_mode,
                    info.st_ino,
                    info.st_dev,
                    info.st_nlink,
                    info.st_uid,
                    info.st_gid,
                    size,
                    info.st_atime,
                    info.st_mtime,
                    info.st_ctime,
                ]
            )
        return info

    with open_mixin, tar_info_mixin, stat_mixin:  # Inject mixins for duration of the build
        return builder_mixin.original(builder, *args, **kwargs)
