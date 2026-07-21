# Release Notes

Human-facing notes for the current release. For the full history see
[CHANGELOG.md](CHANGELOG.md).

---

## Unreleased

This release is a production-readiness pass. There are no new features; it fixes
packaging, dependency, and tooling defects that made the previous releases unsafe to
depend on.

### The one that matters: `agentflow init` was broken on PyPI installs

If you installed `10xscale-agentflow-cli` from PyPI and ran `agentflow init`, scaffolding
failed. The wheel's `package-data` configuration only matched files by extension
(`*.json`, `*.yaml`, `*.yml`, `*.md`, `*.txt`), so four template files were silently
dropped from the built artifact:

```
agentflow_cli/cli/templates/dev/.env.example
agentflow_cli/cli/templates/prod/.env.example
agentflow_cli/cli/templates/prod/.python-version
agentflow_cli/cli/templates/prod/pyproject.toml
```

`init` reads `.env.example` directly, so the failure was unavoidable rather than
cosmetic. Installing from a source checkout hid the problem, which is why it survived
several releases.

Packaging now ships the package tree wholesale, and `CONTRIBUTING.md` documents how to
verify the built artifact rather than trusting the config.

Additionally, the `prod` template shipped a misspelled `.pre-commot-config.yaml`, so
`pre-commit install` in a freshly scaffolded project found no configuration. Renamed.

### Dependencies are now bounded

Every runtime dependency was previously unpinned - `fastapi`, `pydantic`, `uvicorn`,
`typer` and the rest had no floor and no ceiling. A major release of any of them could
break a fresh install with no warning and no way to pin your way out.

All runtime dependencies now carry a verified lower bound, and pre-1.0 or
major-version-risky ones carry an upper cap:

```
10xscale-agentflow>=0.9.0,<2.0
fastapi>=0.116,<1.0
pydantic>=2.13,<3
pydantic-settings>=2.3,<3
uvicorn>=0.30,<1.0
typer>=0.17,<1.0
...
```

**Upgrade note:** if you were resolving an older `fastapi` or `pydantic` alongside this
package, your environment may now resolve differently. The floors are the versions the
test suite is verified against.

### `agentflow version` reported the wrong thing

It read the version out of `pyproject.toml` at a path that does not exist inside an
installed wheel, so it printed `unknown`. It now resolves from installed distribution
metadata and reports the core `10xscale-agentflow` version alongside the CLI version.

### Type information now ships

The package had no `py.typed` marker, so type checkers in downstream projects treated
every import from `agentflow_cli` as `Any`. The marker is now included (PEP 561).

### Removed

`agentflow_cli/src/app/routers/a2a.py` and `a2ui.py` are gone. Both were entirely
commented out and never mounted by `setup_router.init_routes`; they shipped in the wheel
as dead code. Nothing imported them, so nothing breaks. They remain in git history for
whenever the A2A surface is actually built.

### Project and CI hygiene

- CI now runs on pushes to `main`, not only on pull requests, and covers both Python 3.12
  and 3.13 rather than 3.13 alone.
- The release workflow depends on a passing test job. It previously built and attached
  artifacts without running a single test.
- mypy is configured and enforced; CodeQL scanning and Dependabot are enabled.
- Tests requiring real Redis/Postgres are gated behind `pytest --integration`.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, issue forms, and
  a pull request template were added.

### Upgrading

```bash
pip install --upgrade 10xscale-agentflow-cli
```

No code changes are required. If you previously worked around the missing templates by
installing from source, you can switch back to the PyPI package.
