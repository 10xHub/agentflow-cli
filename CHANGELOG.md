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

- Full-canvas animated command intro: an eased block-letter `AGENTFLOW` reveal
  with a moving light front, a flowing gradient field, a typed tagline, and a
  per-command pipeline that fills in as the intro plays. It runs on a temporary
  alternate screen and hands the terminal back, so the animation gets the whole
  canvas while the command's real output stays in scrollback.
- Persistent branded session header (gradient rules, command, version, and
  subtitle) printed into the normal buffer after the intro.
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
- Opt-in `--fullscreen` (or `AGENTFLOW_FULLSCREEN=1`) that runs a command on a
  painted alternate screen and holds it until you press Enter.
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
- The alternate screen is no longer held for a command's whole lifetime. A terminal
  discards an alternate screen when it is released, so that approach erased each
  command's output on exit and made short commands look like a flash of nothing.
  Motion now owns the screen only while it is playing; results are written to the
  normal buffer. `--fullscreen` restores the held-screen behavior for anyone who
  wants it, and pauses before releasing so nothing is lost.
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
