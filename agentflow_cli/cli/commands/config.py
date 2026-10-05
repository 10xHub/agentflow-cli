"""Config command implementation: a browser editor for ``agentflow.json``."""

import webbrowser
from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.config_editor import ConfigEditorServer
from agentflow_cli.cli.constants import DEFAULT_CONFIG_FILE
from agentflow_cli.cli.exceptions import ServerError


class ConfigCommand(BaseCommand):
    """Serve the config editor until the user stops it with Ctrl+C."""

    def execute(
        self,
        config: str = DEFAULT_CONFIG_FILE,
        port: int = 0,
        open_browser: bool = True,
        **kwargs: Any,
    ) -> int:
        config_path = Path(config).expanduser().resolve()
        try:
            server = ConfigEditorServer(config_path, port=port)
        except OSError as exc:
            return self.handle_error(
                ServerError(
                    f"Could not start the config editor: {exc}", host="127.0.0.1", port=port
                )
            )

        self.output.command_header(
            "config",
            "Edit agentflow.json in your browser",
            hint="Ctrl+C to stop the config editor",
        )
        self.output.completion_screen(
            "Config editor running",
            "Open the link below to edit, validate, and save your configuration.",
            details={
                "Editor": server.url,
                "File": f"{config_path}{'' if config_path.exists() else ' (new)'}",
            },
            next_steps=["Press Ctrl+C to stop the editor when you are done."],
        )
        if open_browser:
            webbrowser.open_new_tab(server.url)

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
        return 0
