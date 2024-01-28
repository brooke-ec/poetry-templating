import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Type

from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.console_events import COMMAND
from cleo.io.io import IO
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.console.commands.command import Command
from poetry.factory import Factory
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.poetry import Poetry
from poetry.puzzle.provider import Indicator

from poetry_templating import DEFAULT_BUILD_DIR
from poetry_templating.util import Mixin


@contextmanager
def progress(io: IO, message: str) -> Iterator[None]:
    if not io.output.is_decorated():
        io.write_line(message)
        yield
    else:
        indicator = Indicator(io, "{message}{context}<debug>({elapsed:2s})</debug>")

        with indicator.auto(message, message):
            yield


class EvaluateCommand(Command):
    name: str = "templating evaluate"
    description = "Evaluate templates in the current directory."

    def handle(self) -> int:
        from poetry_templating.engine import TemplatingEngine

        engine = TemplatingEngine(self.poetry.pyproject)
        with progress(self.io, "<info>Evaluating templates...</info>"):
            count = engine.evaluate_and_replace()
        self.line(f"<info>Evaluated templates in {count} files!</info>")
        return 0


class TemplatingPlugin(ApplicationPlugin):
    @property
    def commands(self) -> List[Type[Command]]:
        return [EvaluateCommand]

    def activate(self, application: Application):
        application.event_dispatcher.add_listener(COMMAND, self.on_command)  # type: ignore
        self.root = Path(os.path.dirname(application.poetry.pyproject.path))
        self.poetry = application.poetry
        super().activate(application)

    def on_command(self, event: ConsoleCommandEvent, *_) -> None:
        # If command is build command, set up build templating
        command = event.command
        if isinstance(command, BuildCommand):
            self.setup_build(command)

    def setup_build(self, command: BuildCommand):
        # Mixin to point builders to evaluated clone project
        @Mixin.mixin(command, "handle")
        def handler_mixin() -> int:
            with build_mixin, self.evaluated_clone(command.io) as poetry:
                command._poetry = poetry
                return handler_mixin.original()

        # Mixin to set the "target_dir" parameter back to the original project
        @Mixin.mixin(command, "_build")
        def build_mixin(*args, target_dir=None, **kwargs) -> None:
            target_dir = self.root / DEFAULT_BUILD_DIR
            build_mixin.original(*args, **kwargs, target_dir=target_dir)

        handler_mixin.inject()  # Inject handler mixin to this instance of BuildCommand

    @contextmanager
    def evaluated_clone(self, io: IO) -> Iterator[Poetry]:
        from poetry_templating.engine import TemplatingEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            with progress(io, "Evaluating templates..."):
                shutil.copytree(self.root, tmpdir, symlinks=False, dirs_exist_ok=True)

                # Create clone poetry instance
                poetry = Factory().create_poetry(Path(tmpdir), io=io)

                # Evaluate clone
                engine = TemplatingEngine(poetry.pyproject)
                engine.evaluate_and_replace()
            yield poetry
