"""
Evals router — serves eval-report data over HTTP so the playground's Evals
inspector can exercise a real API. Reports are read from `agentflow eval`'s
JSON output (`eval_reports/*.json`); see EvalReportService for how the
`EvalReport` schema (no run-number, no dollar cost, no built-in regression)
is adapted into the run/detail shape the UI expects.

Endpoints:
    GET /v1/evals/runs            -> list of runs (summary rows)
    GET /v1/evals/runs/{run_id}   -> full drilldown for one run
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from agentflow_cli.src.app.routers.evals.services.eval_report_service import EvalReportService
from agentflow_cli.src.app.utils.response_helper import success_response


# Evals is a dev-only report viewer over local `eval_reports/*.json` files -- it exposes no
# user data and is not a production surface, so it carries no authorization (the paths are
# on the route-guard's public allowlist). See core/auth/route_guard.py.
router = APIRouter(tags=["evals"])


@router.get("/v1/evals/runs", summary="List eval runs")
async def list_eval_runs(request: Request):
    """List all eval runs (summary rows) found under eval_reports/."""
    service = EvalReportService()
    return success_response({"runs": service.list_runs()}, request)


@router.get("/v1/evals/runs/{run_id}", summary="Get eval run detail")
async def get_eval_run(run_id: str, request: Request):
    """Return the full drilldown for one eval run."""
    service = EvalReportService()
    return success_response(service.get_run_detail(run_id), request)
