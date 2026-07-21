# Contributing to 10xScale Agentflow CLI

Thanks for helping out. This document covers setup, the checks your change has to pass,
and what we look for in a pull request.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Scope of this repository

This repo is the **API server and CLI layer** (`10xscale-agentflow-cli`). The core
orchestration engine - `StateGraph`, `ToolNode`, state, persistence, memory - lives in
the separate [`10xscale-agentflow`](https://github.com/10xHub/agentflow) package. If your
change is about graph execution rather than serving or scaffolding, it likely belongs
there.

## Setup

Requires Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/10xHub/agentflow-cli.git
cd agentflow-cli
uv sync --dev
uv run pre-commit install
```

## The checks

Everything below runs in CI. Run it locally before opening a pull request.

```bash
uv run pytest                       # tests + 80% branch-coverage gate
uv run pytest --integration         # adds tests needing real Redis/Postgres
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pre-commit run --all-files   # the full gate: ruff, bandit, hygiene hooks
```

Notes:

- Coverage is enforced at 80% with branch coverage on. A pull request that drops coverage
  below the gate fails.
- Tests must not make unmocked outbound network calls.
- Tests that need real external services must be marked `@pytest.mark.integration` so
  they stay behind the `--integration` flag.
- `agentflow_cli/cli/templates/` is excluded from ruff, mypy, and bandit. It is emitted
  scaffolding, not library code, and references modules that only exist once a project is
  scaffolded.

## Making a change

1. Branch off `main`.
2. Write the test first when you can. New behaviour needs a test; a bug fix needs a test
   that fails before the fix.
3. Update `CHANGELOG.md` under `[Unreleased]`, in the right subsection
   (`Added` / `Changed` / `Fixed` / `Removed` / `Breaking`).
4. Update `README.md` if you changed a CLI flag, an HTTP route, or an `agentflow.json`
   key.
5. Open the pull request against `main` and fill in the template.

### Public API changes

Anything exported from `agentflow_cli`, any CLI command or flag, any HTTP route, and any
`agentflow.json` key is public surface. It is governed by the compatibility policy at the
top of [CHANGELOG.md](CHANGELOG.md): nothing is removed without a deprecation cycle, moved
modules keep a shim for at least one minor release, and breaking changes are documented
under a `### Breaking` heading with migration steps.

### Touching templates

`agentflow_cli/cli/templates/` ships inside the wheel, including dotfiles
(`.env.example`, `.python-version`) and `prod/pyproject.toml`. If you add a file there,
verify it survives packaging:

```bash
uv build
python -c "import zipfile,glob; print(*zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist(), sep='\n')" | grep templates
```

Never assume config that "looks right" is shipping the file. Check the artifact.

### Security-sensitive changes

Auth, authorization, the route guard, and rate limiting are enforcement code. Changes
there need a test that exercises the *denial* path, not only the allow path. See
`tests/integration_tests/test_isolation_idor.py` for the pattern.

Do not report a vulnerability through a pull request or issue. See
[SECURITY.md](SECURITY.md).

## Commit and pull request expectations

- One logical change per pull request. Split refactors from behaviour changes.
- Write commit subjects in the imperative mood: `fix wheel packaging for template dotfiles`.
- Explain *why* in the pull request body, not just what.
- Rebase on `main` rather than merging it in.
- CI must be green. Do not mark a pull request ready while a check is failing.

## Releasing

Maintainers only. See the release procedure in
[PRODUCTION_READINESS.md](../PRODUCTION_READINESS.md) and `RELEASE_NOTES.md`. Releases are
cut by pushing a `vX.Y.Z` tag matching `pyproject.toml`; the workflow refuses to build if
they disagree. Publishing to PyPI is a deliberate manual `make publish`.
