"""A2A server command implementation."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import (
    DEFAULT_A2A_DESCRIPTION,
    DEFAULT_A2A_HOST,
    DEFAULT_A2A_NAME,
    DEFAULT_A2A_PORT,
    DEFAULT_A2A_VERSION,
    DEFAULT_CONFIG_FILE,
)
from agentflow_cli.cli.core.config import ConfigManager
from agentflow_cli.cli.core.validation import validate_cli_options
from agentflow_cli.cli.exceptions import ConfigurationError, ServerError


class A2ACommand(BaseCommand):
    """Command to start an A2A-protocol-compliant agent server."""

    def execute(
        self,
        config: str = DEFAULT_CONFIG_FILE,
        host: str = DEFAULT_A2A_HOST,
        port: int = DEFAULT_A2A_PORT,
        name: str | None = None,
        description: str | None = None,
        streaming: bool = False,
        **kwargs: Any,
    ) -> int:
        try:
            self.output.print_banner(
                "A2A Server",
                "Starting A2A-protocol agent server via Uvicorn.",
            )

            # Validate host/port/config
            validated_options = validate_cli_options(host, port, config)

            # Load agentflow.json
            config_manager = ConfigManager()
            actual_config_path = config_manager.find_config_file(validated_options["config"])
            config_data = config_manager.load_config(str(actual_config_path))

            # Load .env
            env_file_path = config_manager.resolve_env_file()
            if env_file_path:
                self.logger.info("Loading environment from: %s", env_file_path)
                load_dotenv(env_file_path)
            else:
                load_dotenv()

            # Make user graph importable
            os.environ["GRAPH_PATH"] = str(actual_config_path)
            sys.path.insert(0, str(actual_config_path.parent))
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            # Read optional "a2a" section from agentflow.json
            a2a_config: dict[str, Any] = config_data.get("a2a") or {}

            # Resolve final values: CLI flag > agentflow.json > defaults
            agent_name = name or a2a_config.get("name") or DEFAULT_A2A_NAME
            agent_description = description or a2a_config.get("description") or DEFAULT_A2A_DESCRIPTION
            use_streaming = streaming or bool(a2a_config.get("streaming", False))
            agent_version = a2a_config.get("version") or DEFAULT_A2A_VERSION
            executor_path: str | None = a2a_config.get("executor")
            skills_config: list[dict] = a2a_config.get("skills") or []

            agent_url = f"http://{validated_options['host']}:{validated_options['port']}/"

            self.logger.info(
                "Starting A2A server: name=%s, host=%s, port=%d, streaming=%s",
                agent_name,
                validated_options["host"],
                validated_options["port"],
                use_streaming,
            )

            # ---------------------------------------------------------------- #
            # Import a2a-sdk — give a clear error if not installed             #
            # ---------------------------------------------------------------- #
            try:
                from a2a.server.apps import A2AStarletteApplication
                from a2a.server.request_handlers import DefaultRequestHandler
                from a2a.server.tasks import InMemoryTaskStore
                from a2a.types import AgentSkill
            except ImportError as exc:
                raise ServerError(
                    "a2a-sdk is not installed. "
                    "Run: pip install 'agentflow-cli[a2a]'  or  pip install a2a-sdk",
                    host=host,
                    port=port,
                ) from exc

            # ---------------------------------------------------------------- #
            # Import agentflow a2a helpers                                      #
            # ---------------------------------------------------------------- #
            try:
                from agentflow.a2a_integration import make_agent_card
                from agentflow.a2a_integration.executor import AgentFlowExecutor
            except ImportError as exc:
                raise ServerError(
                    "agentflow a2a_integration is not available. "
                    "Make sure you have 'agentflow[a2a_sdk]' installed.",
                    host=host,
                    port=port,
                ) from exc

            # ---------------------------------------------------------------- #
            # Load the CompiledGraph                                            #
            # ---------------------------------------------------------------- #
            import asyncio

            from agentflow_cli.src.app.loader import load_graph

            agent_path: str = config_data["agent"]
            compiled_graph = asyncio.get_event_loop().run_until_complete(
                load_graph(agent_path)
            )

            # ---------------------------------------------------------------- #
            # Build skills list from config (optional)                         #
            # ---------------------------------------------------------------- #
            skills = []
            for s in skills_config:
                skills.append(
                    AgentSkill(
                        id=s.get("id", "run_graph"),
                        name=s.get("name", agent_name),
                        description=s.get("description", agent_description),
                        tags=s.get("tags", []),
                        examples=s.get("examples", []),
                    )
                )

            # ---------------------------------------------------------------- #
            # Build the AgentCard                                               #
            # ---------------------------------------------------------------- #
            card = make_agent_card(
                name=agent_name,
                description=agent_description,
                url=agent_url,
                streaming=use_streaming,
                version=agent_version,
                skills=skills if skills else None,
            )

            # ---------------------------------------------------------------- #
            # Resolve executor — custom class or default AgentFlowExecutor     #
            # ---------------------------------------------------------------- #
            if executor_path:
                try:
                    module_name, class_name = executor_path.rsplit(":", 1)
                    module = importlib.import_module(module_name)
                    executor_cls = getattr(module, class_name)
                    self.logger.info("Loaded custom executor: %s", executor_path)
                    executor = executor_cls(compiled_graph)
                except Exception as exc:
                    raise ConfigurationError(
                        f"Failed to load custom executor '{executor_path}': {exc}",
                        config_path=str(actual_config_path),
                    ) from exc
            else:
                executor = AgentFlowExecutor(compiled_graph, streaming=use_streaming)

            # ---------------------------------------------------------------- #
            # Build and start the A2A server                                   #
            # ---------------------------------------------------------------- #
            handler = DefaultRequestHandler(
                agent_executor=executor,
                task_store=InMemoryTaskStore(),
            )
            starlette_app = A2AStarletteApplication(
                agent_card=card,
                http_handler=handler,
            )

            self.output.info(
                f"A2A agent '{agent_name}' listening on "
                f"http://{validated_options['host']}:{validated_options['port']}/"
            )
            self.output.info(
                f"Agent card: "
                f"http://{validated_options['host']}:{validated_options['port']}"
                f"/.well-known/agent-card.json"
            )

            import uvicorn

            uvicorn.run(
                starlette_app.build(),
                host=validated_options["host"],
                port=validated_options["port"],
            )

            return 0

        except (ConfigurationError, ServerError) as e:
            return self.handle_error(e)
        except Exception as e:
            server_error = ServerError(
                f"Failed to start A2A server: {e}", host=host, port=port
            )
            return self.handle_error(server_error)
