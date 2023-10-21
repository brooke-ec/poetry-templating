import logging
from io import BytesIO, StringIO
from pathlib import Path
from typing import IO as IOType
from typing import BinaryIO, TextIO, cast

from poetry.console.application import Application
from poetry.core.masonry.builder import Builder
from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_plugin_templating.util import Mixin

_log = logging.getLogger(__name__)


class TemplatingPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        builder_mixin.inject()  # Inject builder mixin so that templating is setup when a build is started.


# Mixin to be injected into the Builder.build method to set up the templating system.
@Mixin.mixin(Builder, "build")
def builder_mixin(builder: Builder, *args, **kwargs):
    _log.debug("Setting up Templating System...")
    from poetry_plugin_templating.engine import TemplatingEngine

    # Set up templating engine
    engine = TemplatingEngine(builder._poetry.pyproject)

    # Define replacement for Path.open method
    @Mixin.mixin(Path, "open")
    def open_mixin(path: Path, *args, **kwargs) -> IOType:
        src: IOType = open_mixin.original(path, *args, **kwargs)

        if not engine.should_process(path):
            return src

        # Process file, considering if it was opened in binary mode
        if src.mode == "r":
            text_io: TextIO = cast(TextIO, src)
            processed = engine.process(text_io.read(), path)
            return StringIO(processed)
        if src.mode == "rb":
            binary_io: BinaryIO = cast(BinaryIO, src)
            text = binary_io.read().decode(engine.encoding)
            processed = engine.process(text, path)
            return BytesIO(processed.encode(engine.encoding))
        return src  # Do not process files opened with write capabilities

    with open_mixin:  # Inject mixin for duration of the build
        return builder_mixin.original(builder, *args, **kwargs)
