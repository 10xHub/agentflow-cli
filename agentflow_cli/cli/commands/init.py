"""Init command implementation."""

import contextlib
import json
import re
from pathlib import Path
from string import Template
from typing import Any

import questionary

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.exceptions import FileOperationError, ValidationError


_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_SKIP_DIRS = {"__pycache__", ".ruff_cache"}

# Directories inside prod/ that are only included based on user choices
_AUTH_DIR = "auth"


def _slugify(name: str) -> str:
    """Convert 'WeatherBot' → 'weather-bot'."""
    s = re.sub(r"([A-Z])", r"-\1", name).lstrip("-").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _strip_env_blocks(content: str, *, keep_redis: bool, keep_jwt: bool) -> str:
    """Remove conditional marker blocks that are not needed."""
    if not keep_redis:
        content = re.sub(r"##\[IF_REDIS\]##.*?##\[/IF_REDIS\]##\n?", "", content, flags=re.DOTALL)
    else:
        content = re.sub(r"##\[IF_REDIS\]##\n?", "", content)
        content = re.sub(r"##\[/IF_REDIS\]##\n?", "", content)

    if not keep_jwt:
        content = re.sub(r"##\[IF_JWT\]##.*?##\[/IF_JWT\]##\n?", "", content, flags=re.DOTALL)
    else:
        content = re.sub(r"##\[IF_JWT\]##\n?", "", content)
        content = re.sub(r"##\[/IF_JWT\]##\n?", "", content)

    return content


class InitCommand(BaseCommand):
    """Command to initialize a new agent project interactively."""

    def execute(
        self,
        path: str = ".",
        force: bool = False,
        agent_name: str | None = None,
        template: str | None = None,
        auth: str | None = None,
        rate_limit: str | None = None,
        yes: bool = False,
        non_interactive: bool = False,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> int:
        try:
            self.output.print_banner(
                "Init", "Create a new AgentFlow agent project", color="magenta"
            )

            context: dict[str, Any] | None
            if yes or non_interactive:
                context = self._non_interactive_context(
                    path=path,
                    agent_name=agent_name,
                    template=template,
                    auth=auth,
                    rate_limit=rate_limit,
                )
            else:
                context = self._prompt_user()
            if context is None:
                self.output.info("Cancelled.", emoji=False)
                return 0

            self._print_summary(context)

            base_path = Path(path)
            # Capture this BEFORE any writes: a config file present now is the
            # developer's own (a prior init or a hand edit), and must not be
            # clobbered unless they passed --force.
            config_path = base_path / "agentflow.json"
            config_pre_existed = config_path.exists()

            is_prod = context["setup_type"] == "production"
            template_dir = _TEMPLATES_DIR / ("prod" if is_prod else "dev")

            if dry_run:
                planned = [
                    str(src.relative_to(template_dir))
                    for src in sorted(template_dir.rglob("*"))
                    if src.is_file()
                    and not self._should_skip(src, template_dir, context, is_prod)
                ]
                if "agentflow.json" not in planned:
                    planned.append("agentflow.json")
                self.output.print_list(planned, title="Files that would be created", bullet="→")
                self.output.info("Dry run complete; no files were written.", emoji=False)
                return 0

            base_path.mkdir(parents=True, exist_ok=True)
            self.output.info("Creating project files...", emoji=False)
            created = self._copy_template_dir(
                template_dir, base_path, context, force=force, is_prod=is_prod
            )

            # Regenerate agentflow.json from the built config. Force is safe only to
            # override the copy this run just made; honor --force for a file that was
            # already there.
            config = self._build_config(context, is_prod)
            self._write_file(
                config_path,
                json.dumps(config, indent=2) + "\n",
                force=force or not config_pre_existed,
            )
            if config_path not in created:
                self._print_file_line(config_path, base_path)

            agent_name = context["agent_name"]
            self.output.success(f'Project "{agent_name}" ready at {base_path.resolve()}')

            self._print_next_steps(context, is_prod)

            return 0

        except (FileOperationError, ValidationError) as e:
            return self.handle_error(e)
        except Exception as e:
            return self.handle_error(FileOperationError(f"Failed to initialize project: {e}"))

    def _non_interactive_context(
        self,
        *,
        path: str,
        agent_name: str | None,
        template: str | None,
        auth: str | None,
        rate_limit: str | None,
    ) -> dict[str, Any]:
        """Resolve a complete, reproducible scaffold recipe without prompting."""
        resolved_template = (template or "quick-start").strip().lower().replace("_", "-")
        if resolved_template not in {"quick-start", "production"}:
            raise ValidationError(
                f"Invalid template '{resolved_template}'. Choose quick-start or production.",
                field="template",
            )

        inferred_name = Path(path).resolve().name if path not in {"", "."} else "MyAgent"
        resolved_name = (agent_name or inferred_name).strip()
        slug = _slugify(resolved_name)
        if not resolved_name or not slug:
            raise ValidationError(
                "Agent name must contain at least one letter or number.",
                field="name",
            )

        resolved_auth = (auth or "none").strip().lower()
        if resolved_auth not in {"none", "jwt", "custom"}:
            raise ValidationError(
                f"Invalid auth mode '{resolved_auth}'. Choose none, jwt, or custom.",
                field="auth",
            )

        resolved_rate_limit = (rate_limit or "none").strip().lower()
        if resolved_rate_limit not in {"none", "memory", "redis"}:
            raise ValidationError(
                f"Invalid rate-limit mode '{resolved_rate_limit}'. "
                "Choose none, memory, or redis.",
                field="rate_limit",
            )

        if resolved_template == "quick-start" and (
            resolved_auth != "none" or resolved_rate_limit != "none"
        ):
            raise ValidationError(
                "--auth and --rate-limit require --template production.",
                field="template",
            )

        return {
            "agent_name": resolved_name,
            "agent_name_slug": slug,
            "setup_type": "production"
            if resolved_template == "production"
            else "quick_start",
            "auth": resolved_auth,
            "rate_limit": resolved_rate_limit,
            "rl_requests": 100,
            "rl_window": 60,
            "rl_by": "ip",
            "rl_trusted_proxy": False,
        }

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _prompt_user(self) -> dict | None:  # noqa: PLR0911
        agent_name = questionary.text(
            "What is your agent name?",
            default="MyAgent",
        ).ask()
        if agent_name is None:
            return None

        setup_choice = questionary.select(
            "Quick Start or Production setup?",
            choices=["Quick Start", "Production"],
            default="Quick Start",
        ).ask()
        if setup_choice is None:
            return None

        is_prod = setup_choice == "Production"

        context: dict[str, Any] = {
            "agent_name": agent_name,
            "agent_name_slug": _slugify(agent_name),
            "setup_type": "production" if is_prod else "quick_start",
            "auth": "none",
            "rate_limit": "none",
        }

        if not is_prod:
            return context

        # --- Production questions ---

        auth_choice = questionary.select(
            "Authentication type?",
            choices=["None", "JWT", "Custom"],
            default="None",
        ).ask()
        if auth_choice is None:
            return None
        context["auth"] = auth_choice.lower()

        if context["auth"] == "none":
            return context

        rl_choice = questionary.select(
            "Rate limiting?",
            choices=["None", "Memory Based", "Redis Based"],
            default="None",
        ).ask()
        if rl_choice is None:
            return None
        context["rate_limit"] = {
            "None": "none",
            "Memory Based": "memory",
            "Redis Based": "redis",
        }[rl_choice]

        if context["rate_limit"] != "none":
            rl_requests = questionary.text(
                "Max requests per window?",
                default="100",
                validate=lambda v: (v.isdigit() and int(v) > 0) or "Enter a positive integer",
            ).ask()
            if rl_requests is None:
                return None
            context["rl_requests"] = int(rl_requests)

            rl_window = questionary.text(
                "Window size (seconds)?",
                default="60",
                validate=lambda v: (v.isdigit() and int(v) > 0) or "Enter a positive integer",
            ).ask()
            if rl_window is None:
                return None
            context["rl_window"] = int(rl_window)

            rl_by = questionary.select(
                "Limit by?",
                choices=["Per IP (recommended)", "Global"],
                default="Per IP (recommended)",
            ).ask()
            if rl_by is None:
                return None
            context["rl_by"] = "ip" if "IP" in rl_by else "global"

            rl_proxy = questionary.confirm(
                "Behind a reverse proxy? (reads real IP from forwarded headers)",
                default=False,
            ).ask()
            if rl_proxy is None:
                return None
            context["rl_trusted_proxy"] = rl_proxy

        return context

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _print_summary(self, context: dict) -> None:
        is_prod = context["setup_type"] == "production"
        setup_label = "Production" if is_prod else "Quick Start"

        rows: list[tuple[str, str]] = [
            ("Agent name", context["agent_name"]),
            ("Package name", context["agent_name_slug"]),
            ("Setup", setup_label),
        ]
        if is_prod:
            auth = context["auth"]
            rows.append(("Auth", "None" if auth == "none" else auth.upper()))

            rl = context["rate_limit"]
            if rl == "none":
                rows.append(("Rate limit", "None"))
            else:
                rl_by = "Global" if context.get("rl_by") == "global" else "Per IP"
                proxy = " · proxy headers on" if context.get("rl_trusted_proxy") else ""
                rows.append(
                    (
                        "Rate limit",
                        f"{rl.capitalize()} · {context.get('rl_requests', 100)} req / "
                        f"{context.get('rl_window', 60)}s · {rl_by}{proxy}",
                    )
                )

        self.output.print_table(
            ["Setting", "Value"],
            [[label, value] for label, value in rows],
            title="Project summary",
        )

    def _print_file_line(self, dest: Path, base_path: Path) -> None:
        rel = dest.relative_to(base_path)
        self.output.info(f"Created {rel}", emoji=False)

    def _print_next_steps(self, context: dict, is_prod: bool) -> None:
        steps: list[tuple[str, str]] = []

        steps.append(("agentflow skills", "Install coding agent skills"))

        if is_prod:
            steps.append(("pre-commit install", "Set up Git hooks (ruff, bandit, etc.)"))

        steps.append(("pip install google-genai", "Add the AI provider library"))
        steps.append(("cp .env.example .env", "Copy env template, then fill in your API keys"))

        if context["auth"] == "jwt":
            steps.append(("# Set JWT_SECRET_KEY in .env", "Required for JWT auth to work"))

        if context["rate_limit"] == "redis":
            steps.append(("# Set REDIS_URL in .env", "Required for Redis rate limiting"))

        steps.append(("agentflow play", "Launch your agent"))

        self.output.print_table(
            ["#", "Command", "Purpose"],
            [
                [str(index), command, description]
                for index, (command, description) in enumerate(steps, 1)
            ],
            title="Next steps",
        )

    # ------------------------------------------------------------------
    # Config generation
    # ------------------------------------------------------------------

    def _build_config(self, context: dict, is_prod: bool) -> dict:
        config: dict = {
            "agent": "graph.agent:app",
            "env": ".env",
            "auth": None,
            "thread_name_generator": None,
        }

        if not is_prod:
            return config

        auth = context["auth"]
        if auth == "jwt":
            config["auth"] = {"method": "jwt"}
        elif auth == "custom":
            config["auth"] = {"method": "custom", "path": "auth.agent_auth:AgentAuth"}

        if auth in ("jwt", "custom"):
            # Secure by default in production: a thread is accessible only to its owner.
            # Change to "allow_all" to let any authenticated user access any thread, or
            # point at a custom AuthorizationBackend ("module:attr").
            config["authorization"] = "ownership"

        config["thread_name_generator"] = "graph.thread_name_generator:MyNameGenerator"
        config["injectq"] = "graph.agent:container"

        rate_limit = context["rate_limit"]
        if rate_limit != "none":
            config["rate_limit"] = {
                "enabled": True,
                "backend": rate_limit,
                "requests": context.get("rl_requests", 100),
                "window": context.get("rl_window", 60),
                "by": context.get("rl_by", "ip"),
                "trusted_proxy_headers": context.get("rl_trusted_proxy", False),
                "exclude_paths": ["/health", "/docs", "/redoc", "/openapi.json"],
            }

        return config

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _should_skip(self, src: Path, template_dir: Path, context: dict, is_prod: bool) -> bool:
        """Return True if this template file should not be copied."""
        if any(part in _SKIP_DIRS for part in src.parts):
            return True
        if not is_prod:
            return False
        # auth/ is only included for custom auth; skip for none and jwt
        rel_parts = src.relative_to(template_dir).parts
        return rel_parts[0] == _AUTH_DIR and context["auth"] != "custom"

    def _render(self, src: Path, context: dict, is_prod: bool) -> str:
        content = src.read_text(encoding="utf-8")

        # Strip conditional blocks in .env.example before substitution
        if src.name == ".env.example" and is_prod:
            content = _strip_env_blocks(
                content,
                keep_redis=context["rate_limit"] == "redis",
                keep_jwt=context["auth"] == "jwt",
            )

        with contextlib.suppress(Exception):
            content = Template(content).safe_substitute(context)

        return content

    def _copy_template_dir(
        self,
        template_dir: Path,
        dest_dir: Path,
        context: dict,
        *,
        force: bool,
        is_prod: bool,
    ) -> set[Path]:
        created: set[Path] = set()
        for src in sorted(template_dir.rglob("*")):
            if src.is_dir():
                continue
            if self._should_skip(src, template_dir, context, is_prod):
                continue
            rel = src.relative_to(template_dir)
            dest = dest_dir / rel
            content = self._render(src, context, is_prod)
            self._write_file(dest, content, force=force)
            self._print_file_line(dest, dest_dir)
            created.add(dest)
        return created

    def _write_file(self, path: Path, content: str, *, force: bool) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and not force:
                raise FileOperationError(
                    f"File already exists: {path}. Use --force to overwrite.",
                    file_path=str(path),
                )
            path.write_text(content, encoding="utf-8")
            self.logger.debug("Wrote file: %s", path)
        except OSError as e:
            raise FileOperationError(
                f"Failed to write file {path}: {e}", file_path=str(path)
            ) from e
