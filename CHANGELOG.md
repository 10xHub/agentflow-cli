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

- Terminal-native frame animation for interactive commands, plus reusable
  animated activities, timed state transitions, and completion panels.
- Staged startup feedback and connected-playground completion output for
  `agentflow play` and `agentflow dev`.
- Adaptive `--animation` / `--no-animation` controls with CI, pipe, JSON, and
  accessibility-safe fallbacks.
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
