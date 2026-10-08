"""The deprecated ``agentflow_cli`` import name aliases ``tenxgraph_api`` until 2.0."""

import subprocess
import sys
import textwrap


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_public_exports_resolve_through_the_alias():
    res = _run("from agentflow_cli import BaseAuth; print(BaseAuth.__name__)")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "BaseAuth"


def test_objects_are_identical_to_tenxgraph_api():
    res = _run(
        """
        import sys
        import agentflow_cli
        import tenxgraph_api
        from agentflow_cli.src.app.core.auth.base_auth import BaseAuth as Old
        from tenxgraph_api.src.app.core.auth.base_auth import BaseAuth as New
        import agentflow_cli.cli.constants as old_constants
        import tenxgraph_api.cli.constants as new_constants
        assert agentflow_cli is tenxgraph_api
        assert Old is New
        assert old_constants is new_constants
        assert new_constants.__spec__.name == "tenxgraph_api.cli.constants"
        print("ok")
        """
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "ok"


def test_deprecation_warning_emitted_once():
    res = _run(
        """
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import agentflow_cli
            import agentflow_cli.cli.constants
            import agentflow_cli.src.app.core.auth.base_auth
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)
               and "tenxgraph_api" in str(w.message)]
        assert len(dep) == 1, dep
        print("ok")
        """
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "ok"


def test_unknown_submodule_raises():
    res = _run("import agentflow_cli.does_not_exist")
    assert res.returncode != 0
    assert "ModuleNotFoundError" in res.stderr
