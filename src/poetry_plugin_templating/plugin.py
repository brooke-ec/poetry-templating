from poetry.console.application import Application
from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_plugin_templating.mixin import builder_mixin


class TemplatingPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        builder_mixin.inject()
