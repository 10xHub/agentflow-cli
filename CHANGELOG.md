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
  into `play`/`dev`/`api`, `init`, `build`, `test`, and `doctor`.
- Determinate progress with a running pass/fail tally
  (`OutputFormatter.progress_run`), used by `agentflow eval` so per-case results
  scroll above a bar that reports completion, counts, and elapsed time.
- Shared brand palette and glyph sets (`cli/core/theme.py`) with continuous
  gradient sampling and a complete ASCII fallback set.
- Command-specific intro signatures and taglines for `play`, `dev`, `api`,
  `init`, `build`, `test`, `eval`, `doctor`, and `skills`, previewable with the
  side-effect-free `agentflow demo`.
- Row-by-row reveal for completion panels.
- Staged startup feedback, a pre-flight port check, and connected-playground
  completion output for `agentflow play` and `agentflow dev`.
- Adaptive `--animation` / `--no-animation` controls with CI, pipe, JSON, and
  accessibility-safe fallbacks. Every animated surface has a plain
  line-per-transition renderer and a versioned JSON/JSONL event renderer.
- Adaptive Rich terminal rendering with TTY/CI detection, plain/JSONL modes,
  `NO_COLOR` support, ASCII fallback, quiet mode, and shared status rendering.
- Root `--format`, `--json`, `--color`, `--no-color`, `--progress`, `--cwd`,
  `--yes`, `--non-interactive`, `--debug`, and `-V/--version` options.
- `agentflow dev` as the goal-oriented local development command; `api` and `play`
  remain available for compatibility.
- `agentflow doctor` package, evaluation API, project configuration, and port checks.
- Cross-platform `agentflow config list|get|set|unset|path|validate` user preferences.
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
