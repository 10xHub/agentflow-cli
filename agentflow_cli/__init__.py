"""Deprecated alias for :mod:`tenxgraph_api`.

``agentflow_cli`` is the old import name of the 10xGraph API server and is kept until 2.0.
Every ``agentflow_cli`` and ``agentflow_cli.<sub>`` import resolves to the *same module
object* as ``tenxgraph_api`` / ``tenxgraph_api.<sub>``, so ``isinstance`` checks and
module-level singletons are shared rather than duplicated. New code should use
``tenxgraph_api``.
"""

import importlib
import importlib.abc
import importlib.util
import sys
import warnings


_OLD = "agentflow_cli"
_NEW = "tenxgraph_api"


class _AliasLoader(importlib.abc.Loader):
    """Hand back the already-importable ``tenxgraph_api`` module under the old name."""

    def __init__(self, real_name: str) -> None:
        self._real_name = real_name
        self._real_spec = None

    def create_module(self, spec):
        module = importlib.import_module(self._real_name)
        # The import machinery overwrites ``module.__spec__`` with the alias spec.
        self._real_spec = module.__spec__
        return module

    def exec_module(self, module) -> None:
        # Already executed under its real name; restore the real spec.
        if self._real_spec is not None:
            module.__spec__ = self._real_spec


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(_OLD + "."):
            return None
        real_name = _NEW + fullname[len(_OLD) :]
        try:
            real_spec = importlib.util.find_spec(real_name)
        except (ImportError, ValueError):
            return None
        if real_spec is None:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            _AliasLoader(real_name),
            is_package=real_spec.submodule_search_locations is not None,
        )


if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

warnings.warn(
    "The 'agentflow_cli' import name is deprecated and will be removed in 2.0; "
    "import 'tenxgraph_api' instead (for example 'from tenxgraph_api import BaseAuth').",
    DeprecationWarning,
    stacklevel=2,
)

# Make ``import agentflow_cli`` itself return the real package object.
sys.modules[_OLD] = importlib.import_module(_NEW)
