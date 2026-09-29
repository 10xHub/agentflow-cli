"""AG-UI protocol endpoint (``POST /v1/ag-ui``).

Needs the optional ``ag-ui-protocol`` package, so it is only imported when ``ag_ui.enabled``
is set in agentflow.json.
"""

from .router import router


__all__ = ["router"]
