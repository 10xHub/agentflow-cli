# Changelog

All notable changes to `10xscale-agentflow-cli` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Compatibility policy

- **Nothing public is removed without a deprecation cycle.** A public name (anything
  exported from `agentflow_cli`, a CLI command or flag, an HTTP route, or an
  `agentflow.json` key) is first marked deprecated in a release, kept working for at
  least one subsequent minor release, and only then removed in a major release.
- **Moved modules keep a back-compat shim** re-exporting from the new location for at
  least one minor release. Import paths do not break silently.
- **Breaking changes are documented under a `### Breaking` heading** in the release's
  section, with the migration step spelled out.
- Anything under `agentflow_cli.cli.templates/` is emitted scaffolding, not API; template
  content can change in any release.

---

## [Unreleased]

### Added

- **AG-UI endpoint (`POST /v1/ag-ui`)** serves the graph over the
  [AG-UI protocol](https://docs.ag-ui.com), so AG-UI clients such as CopilotKit
  (through its generic `HttpAgent`) can use an Agentflow agent. Off by default: set
  `"ag_ui": {"enabled": true}` in `agentflow.json` and install the new `ag-ui` extra
  (`pip install "10xscale-agentflow-cli[ag-ui]"`, `ag-ui-protocol>=1.0,<2`). The server
  refuses to start with a clear install hint when the endpoint is enabled but the package
  is missing. The route uses the `graph:stream` permission and checks `threadId`
  ownership when auth is configured. Streams text and reasoning, tool calls and results,
  node steps, application state (`STATE_SNAPSHOT`), and `interrupt()` pauses (`RUN_FINISHED`
  with an `interrupt` outcome, answered through `RunAgentInput.resume`; `cancelled` resumes
  with `None`). The thread's checkpoint is the record of the conversation, so only new user
  messages and tool results from the client reach the graph. Browser tools the client sends
  (`RunAgentInput.tools`, e.g. CopilotKit `useFrontendTool`) are offered to the model for that
  run with no `agentflow.json` entry. `RunAgentInput.context`, `tools` and `forwardedProps`
  are available to nodes as `config["ag_ui"]`. `agentflow init` writes
  `"ag_ui": {"enabled": false}`, and `agentflow config` shows the new section. Requires the
  `10xscale-agentflow` release that adds `interrupt()` and per-run `remote_tools`.
- **`resume` on `/v1/graph/invoke` and `/v1/graph/stream`.** Resumes a thread paused by
  `interrupt()`; `messages` may be empty when `resume` is sent.
- **`remote_tools` is a server-owned run-config key.** Client config can no longer set it on
  any route; only adapters whose clients bring tools by protocol (AG-UI) fill it.
- `GraphService.stream_chunks()` yields the graph stream as `StreamChunk` objects, with an
  optional `server_config` for server-owned run config; `stream_graph()` (NDJSON) is now a
  thin wrapper over it.

- **`agentflow skills --validate PATH`** checks a skill directory, or a folder of
  skill directories, against the Agent Skills specification (agentskills.io).
  It reports errors and warnings per skill and exits `1` when any skill is
  invalid. The option is repeatable, and it requires a `10xscale-agentflow`
  release that ships `agentflow.core.skills.validate_skill`.
- **The bundled Agentflow skill conforms to the Agent Skills specification.** Its
  `description` was invalid YAML (an unquoted `TRIGGER when:`), so strict parsers,
  including Agentflow's own loader, rejected it. Codex, Claude and GitHub now all
  receive one identical `SKILL.md` that references `references/...` relative to
  the skill directory, instead of three copies hard-wired to one install path
  each.
- **Persistent full-screen application surface.** On an interactive terminal a
  command now runs on its own screen with branded chrome pinned in place: a
  header (gradient rule, identity, version, subtitle) at the top, a footer
  status bar at the bottom, and the command's output scrolling between them.
  Pinning uses a DEC scrolling region, so it survives output from child
  processes — pytest, Uvicorn, Questionary prompts — without routing any of it
  through a renderer. The screen is held until you press Enter, and released
  through a `finally` guard so a crash can never leave your shell on an
  alternate buffer or inside a scrolling region. Opt out with `--no-fullscreen`
  or `AGENTFLOW_NO_FULLSCREEN=1`.
- Full-canvas animated command intro: an eased block-letter `AGENTFLOW` reveal
  with a moving light front, a flowing gradient field, a typed tagline, and a
  per-command pipeline that fills in as the intro plays. Inside the full-screen
  surface it collapses into the pinned header; with `--no-fullscreen` it plays
  on a temporary screen and leaves a durable header in your scrollback.
- Live step timelines (`OutputFormatter.timeline`): a command declares its stages
  up front, so pending work is visible from the first frame while the running
  stage animates with a spinner, elapsed timer, and a live detail line. Wired
  into `play`/`dev`/`api`, `init`, `build`, `test`, and `audit`.
- Determinate progress with a running pass/fail tally
  (`OutputFormatter.progress_run`), used by `agentflow eval` so per-case results
  scroll above a bar that reports completion, counts, and elapsed time.
- Shared brand palette and glyph sets (`cli/core/theme.py`) with continuous
  gradient sampling and a complete ASCII fallback set.
- Command-specific intro signatures and taglines for `play`, `dev`, `api`,
  `init`, `build`, `test`, `eval`, `audit`, and `skills`, previewable with the
  side-effect-free `agentflow demo` (`--style all|typing|network|init|build|eval`).
- Row-by-row reveal for completion panels.
- **Shared guided-prompt layer** (`cli/core/prompts.py`). Every interactive
  question now runs through one themed service, so prompts share a palette, a
  cancellation contract (Ctrl+C returns to a clean exit rather than a
  traceback), and one non-interactive policy.
- `agentflow skills` picks agents with an arrow-key list where **space toggles**
  and enter confirms, instead of typing a menu number. Each row shows its
  install path, already-installed agents are labelled and pre-checked, and
  choosing one that exists offers to overwrite rather than failing.
- `agentflow skills` reports installs through a timeline and a completion
  screen, matching every other command.
- `agentflow init` prompts now explain each option inline — what Quick Start
  versus Production scaffolds, what each auth mode requires, what each rate
  limit backend costs.
- Staged startup feedback, a pre-flight port check, and connected-playground
  completion output for `agentflow play` and `agentflow dev`.
- Adaptive `--animation` / `--no-animation` controls with CI, pipe, JSON, and
  accessibility-safe fallbacks. Every animated surface has a plain
  line-per-transition renderer and a versioned JSON/JSONL event renderer.
- Adaptive Rich terminal rendering with TTY/CI detection, plain/JSONL modes,
  `NO_COLOR` support, ASCII fallback, quiet mode, and shared status rendering.
- Root `--format`, `--json`, `--color`, `--no-color`, `--progress`,
  `--animation/--no-animation`, `--fullscreen/--no-fullscreen`, `--cwd`,
  `--yes`, `--non-interactive`, `--debug`, and `-V/--version` options.
- `agentflow dev` as the goal-oriented local development command (config, host,
  port, `--reload/--no-reload`, `--open/--no-open`); `api` and `play` remain
  available for compatibility.
- `agentflow audit`: six read-only checks — Python interpreter, installed
  `10xscale-agentflow-cli`, installed `10xscale-agentflow`, whether the installed
  core still exposes the evaluation API `agentflow eval` imports, whether
  `agentflow.json` exists and declares a valid `agent` key, and whether the
  default port is free. Reported live through the timeline and again as a summary
  table. Exits `1` on any failure and `0` otherwise (warnings do not fail the
  run), so it works as a CI gate; nothing is written or changed.
- `agentflow demo`: preview the animation, timeline, and progress states without
  touching project state.
- Cross-platform `agentflow config list|get|set|unset|path|validate` user
  preferences, stored as JSON in the per-user config directory. `output.format`,
  `output.color`, and `output.progress` are read at startup as defaults; explicit
  flags still win.
- Reproducible `agentflow init --non-interactive` recipes and `--dry-run` previews.
- Stable CLI error codes and dependency recovery suggestions.
- `py.typed` marker, so type information now reaches consumers (PEP 561).
- `--integration` pytest flag gating tests marked `integration` that require real
  Redis/Postgres, so a default `pytest` run needs no external services.
- mypy configuration (`[tool.mypy]`) and a mypy step in CI.
- CodeQL static analysis workflow.
- Dependabot configuration for pip and GitHub Actions updates.
- Community health files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  `RELEASE_NOTES.md`, issue forms, and a pull request template.
- `Changelog` entry in project URLs.

### Changed

- Command implementations are loaded lazily, so a broken optional feature no longer
  prevents root help, version, completion, or unrelated commands from starting.
- CLI logging now uses one invocation-wide handler, so quiet and verbose levels apply
  consistently without duplicate records.
- Project configuration discovery now walks parent directories from the current
  working directory.
- Init, build, and eval status output now flows through the shared renderer instead of
  writing raw ANSI control sequences.
- **The full-screen session no longer erases the command's output.** It used to
  hold the alternate screen through a Rich live display, which re-homes the
  cursor before every write — so each line overwrote the last — and then released
  the screen on exit, which a terminal handles by discarding everything drawn on
  it. Short commands showed a flash of nothing. The frame now switches the buffer
  directly and pauses on a closing hint before letting go.
- The screen is claimed lazily, by the first command that renders a header.
  Script-shaped invocations (`--version`, `config get`, `--format json`) never
  take over the terminal or pause on exit.
- A console that reports itself as a terminal but refuses the alternate buffer
  (legacy Windows console) now aborts the frame before anything is written,
  rather than leaving a scrolling region on the user's real scrollback.
- **A terminal that cannot host a prompt no longer crashes the command.**
  `stdin.isatty()` is true under MSYS/Cygwin shells on Windows, but
  prompt-toolkit cannot attach to a console there and raises — which surfaced as
  `AF-INTERNAL-001: Unexpected error: Found xterm-256color, while expecting a
  Windows console`. Prompt availability is now probed, so such a terminal counts
  as non-interactive and gets the usual "pass --agent or --all" guidance.
- Pinned chrome is repainted after each prompt. Prompt-toolkit erases from the
  cursor to the end of the *screen*, which reaches past the scrolling region and
  took the footer with it.
- One Rich `Console` is now reused per stream. Rebuilding it per call meant a live
  display could not tell that ordinary prints belonged to it, so background output
  collided with spinners and progress bars instead of scrolling above them.
- `agentflow init` no longer prints one line per scaffolded file; files stream through
  the active timeline row instead.

### Fixed

- **Scaffolding templates were missing from the wheel.** The `package-data` globs only
  matched `*.json/*.yaml/*.yml/*.md/*.txt`, silently dropping
  `templates/dev/.env.example`, `templates/prod/.env.example`,
  `templates/prod/.python-version`, and `templates/prod/pyproject.toml`. `agentflow init`
  failed for anyone installing from PyPI. Packaging now ships the package tree wholesale.
- `agentflow version` reported `unknown` for the package version when installed from a
  wheel, because it read `pyproject.toml` from a path that does not exist in an installed
  distribution. It now resolves from installed distribution metadata and additionally
  reports the core `10xscale-agentflow` version.
- The `prod` template shipped `.pre-commot-config.yaml` (typo), so `pre-commit` found no
  config in scaffolded projects. Renamed to `.pre-commit-config.yaml`.
- Branch coverage is now measured by the default `pytest` invocation (`--cov-branch`),
  not only in the CI-specific command.

### Changed

- **Every runtime dependency now has a lower bound**, and pre-1.0 / major-version-risky
  dependencies have an upper cap (`pydantic>=2.13,<3`, `fastapi>=0.116,<1.0`,
  `10xscale-agentflow>=0.9.0,<2.0`, and so on). Previously all runtime dependencies were
  unpinned, so a major release of any of them could break installs without warning.
- Optional extras `snowflakekit`, `redis`, and `jwt` gained bounds.
- CI now runs on pushes to `main` as well as pull requests, and covers both advertised
  Python versions (3.12 and 3.13) rather than 3.13 alone.
- The release workflow now depends on a passing test job; it no longer builds and
  publishes untested code.
- `Documentation` URL points at the published docs site instead of a Read the Docs URL
  that was never provisioned.

### Removed

- `agentflow_cli/src/app/routers/a2a.py` and `a2ui.py`. Both were entirely commented out,
  never mounted by `setup_router.init_routes`, and shipped in the wheel as dead code.
  They can be restored from git history when the A2A surface is actually implemented.
- Design and planning notes from the repository root (`AUTHORIZATION_PLAN.md`,
  `AUTHORIZATION_PLAN_PHASE2.md`, `AGENTFLOW_JSON.md`, `CUSTOM_AUTH.md`).

---

## [0.5.0]

Initial entry in this changelog. Releases before `0.5.0` were not tracked here; see the
GitHub release history for their notes.

[Unreleased]: https://github.com/10xHub/agentflow-cli/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/10xHub/agentflow-cli/releases/tag/v0.5.0
