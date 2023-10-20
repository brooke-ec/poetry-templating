from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.console_events import COMMAND
from cleo.events.event import Event
from cleo.events.event_dispatcher import EventDispatcher
from cleo.io.outputs.output import Verbosity
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_plugin_templating.engine import TemplatingEngine


class TemplatingPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        if application.event_dispatcher is None:
            raise TypeError("event_dispathcer is None.")

        application.event_dispatcher.add_listener(COMMAND, self.on_command)

    def on_command(
        self,
        event: Event,
        event_name: str,
        dispatcher: EventDispatcher,
    ):
        if not isinstance(event, ConsoleCommandEvent):
            raise TypeError("Expected ConsoleCommandEvent")

        command = event.command
        if not isinstance(command, BuildCommand):
            return

        io = event.io
        io.write_line("Setting up templating engine...", Verbosity.DEBUG)

        engine = TemplatingEngine(io, command.poetry.pyproject)
