# What and why

<!-- What does this change, and what problem does it solve? Link the issue: Fixes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change to public API surface
- [ ] Refactor with no behaviour change
- [ ] Documentation
- [ ] Build, CI, or packaging

## Checks

- [ ] `uv run pytest` passes, including the 80% branch-coverage gate
- [ ] `uv run ruff check . && uv run ruff format --check .` is clean
- [ ] `uv run mypy` is clean
- [ ] `uv run pre-commit run --all-files` is clean
- [ ] New behaviour has a test; a bug fix has a test that fails without the fix
- [ ] No unmocked outbound network calls in tests; anything needing real Redis/Postgres is
      marked `@pytest.mark.integration`

## Documentation

- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] `README.md` updated if a CLI flag, HTTP route, or `agentflow.json` key changed
- [ ] Breaking changes are under a `### Breaking` heading with migration steps

## If you touched `agentflow_cli/cli/templates/`

- [ ] I built the wheel and confirmed the new files are inside it, not just in the repo

<!--
  uv build
  python -c "import zipfile,glob;print(*zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist(),sep='\n')" | grep templates
-->

## If you touched auth, authorization, the route guard, or rate limiting

- [ ] There is a test covering the **denial** path, not only the allow path

---

<!--
  Security vulnerabilities do not belong in a pull request or issue.
  See SECURITY.md for the private disclosure channel.
-->
