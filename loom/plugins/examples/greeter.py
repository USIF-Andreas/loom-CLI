"""Example plugin for loom."""
from .. import Plugin


class GreeterPlugin(Plugin):
    name = "greeter"
    version = "0.1.0"
    description = "A simple example plugin"

    def execute(self, action: str, **kwargs) -> str:
        if action == "greet":
            name = kwargs.get("name", "world")
            return f"Hello, {name}!"
        return f"Unknown action: {action}"