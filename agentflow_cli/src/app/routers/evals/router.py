"""
Dummy evals router — serves deterministic eval-report data over HTTP so the
playground's Evals inspector can exercise a real API. There is no real eval store
yet; when `agentflow eval` reports (eval_reports/*.json) become queryable, swap
the in-module DATA for a reader over those files.

Endpoints:
    GET /v1/evals/runs            -> list of runs (summary rows)
    GET /v1/evals/runs/{run_id}   -> full drilldown for one run
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agentflow_cli.src.app.utils.response_helper import success_response

router = APIRouter(tags=["evals"])


# --------------------------------------------------------------------------- #
#  Dummy report data                                                          #
# --------------------------------------------------------------------------- #

_RUNS: list[dict[str, Any]] = [
    {"id": "cs-5", "name": "customer-support", "run": "#5", "rate": 87.5, "status": "pass", "cases": 24, "ago": "2h ago"},
    {"id": "cs-4", "name": "customer-support", "run": "#4", "rate": 91.7, "status": "pass", "cases": 24, "ago": "1d ago"},
    {"id": "rs-3", "name": "refund-simulator", "run": "#3", "rate": 72.0, "status": "fail", "cases": 25, "ago": "1d ago"},
    {"id": "cs-3", "name": "customer-support", "run": "#3", "rate": 91.7, "status": "pass", "cases": 24, "ago": "2d ago"},
    {"id": "tr-2", "name": "tool-routing", "run": "#2", "rate": 96.4, "status": "pass", "cases": 28, "ago": "3d ago"},
    {"id": "cs-2", "name": "customer-support", "run": "#2", "rate": 83.3, "status": "pass", "cases": 24, "ago": "4d ago"},
]

_CS5_CASES: list[dict[str, Any]] = [
    {
        "id": "c1", "name": "greets and identifies intent", "type": "eval",
        "score": 0.94, "status": "pass", "lat": "1.2s", "cost": "$0.004",
        "input": "Hi, I can't log in to my account.",
        "expected": "Acknowledge, ask for the email on file, offer a reset link.",
        "actual": "I'm sorry you're locked out. What's the email on your account? I can send a reset link.",
    },
    {
        "id": "c2", "name": "refund within policy window", "type": "eval",
        "score": 0.88, "status": "pass", "lat": "1.6s", "cost": "$0.005",
        "input": "I want a refund for order #4471, bought 5 days ago.",
        "expected": "Confirm order, verify within 14-day window, initiate refund.",
        "actual": "Order #4471 is within the refund window. I've started your refund; it'll post in 3-5 days.",
    },
    {
        "id": "c3", "name": "refuses out-of-policy refund", "type": "eval",
        "score": 0.62, "status": "fail", "lat": "1.9s", "cost": "$0.006",
        "input": "Refund my order #2200 from 3 months ago.",
        "expected": "Politely decline (outside 14-day window), explain policy, offer store credit alternative.",
        "actual": "Sure, I've processed a full refund for order #2200 to your card.",
        "rubric": [
            {"key": "policy_adherence", "value": 0.35, "tone": "danger"},
            {"key": "correctness", "value": 0.55, "tone": "danger"},
            {"key": "tone", "value": 0.92, "tone": "accent"},
            {"key": "weighted score", "value": 0.62, "tone": "danger"},
        ],
    },
    {
        "id": "c4", "name": "multi-turn: escalation to human", "type": "sim",
        "score": 0.71, "status": "fail", "lat": "4.3s", "cost": "$0.012",
        "input": "(user-simulator) frustrated customer, billing dispute, 6 turns",
        "expected": "De-escalate, gather details, escalate to human after 2 failed resolutions.",
        "actual": "Looped on self-service steps; never offered human handoff.",
        "rubric": [
            {"key": "de_escalation", "value": 0.68, "tone": "danger"},
            {"key": "handoff_trigger", "value": 0.40, "tone": "danger"},
            {"key": "tone", "value": 0.95, "tone": "accent"},
            {"key": "weighted score", "value": 0.71, "tone": "danger"},
        ],
        "conversation": [
            {"role": "sim", "text": "This is the third time I've been charged. Fix it now."},
            {"role": "agent", "text": "I understand. Let's try resetting your billing profile first."},
            {"role": "sim", "text": "I already did that twice. It doesn't work."},
            {"role": "agent", "text": "Let's clear the cache and re-add your card…"},
            {"role": "sim", "text": "Just get me a person!"},
        ],
    },
    {
        "id": "c5", "name": "handles unknown product SKU", "type": "eval",
        "score": 0.79, "status": "fail", "lat": "1.4s", "cost": "$0.004",
        "input": "Where's my order for SKU ZZ-999?",
        "expected": "State SKU not found, ask to confirm order number.",
        "actual": "Let me check... your order is on the way. (hallucinated status)",
        "rubric": [
            {"key": "grounding", "value": 0.42, "tone": "danger"},
            {"key": "correctness", "value": 0.66, "tone": "danger"},
            {"key": "tone", "value": 0.90, "tone": "accent"},
            {"key": "weighted score", "value": 0.79, "tone": "danger"},
        ],
    },
    {
        "id": "c6", "name": "tone stays professional under abuse", "type": "sim",
        "score": 0.91, "status": "pass", "lat": "3.8s", "cost": "$0.010",
        "input": "(user-simulator) hostile customer, 5 turns",
        "expected": "Stay calm and professional, do not mirror hostility.",
        "actual": "Maintained calm tone across all turns; offered concrete help.",
        "rubric": [
            {"key": "composure", "value": 0.94, "tone": "accent"},
            {"key": "helpfulness", "value": 0.86, "tone": "accent"},
            {"key": "tone", "value": 0.93, "tone": "accent"},
            {"key": "weighted score", "value": 0.91, "tone": "accent"},
        ],
        "conversation": [
            {"role": "sim", "text": "You people are useless. This is a joke."},
            {"role": "agent", "text": "I'm sorry this has been frustrating. Let me see exactly what happened on your order."},
            {"role": "sim", "text": "Just do your job."},
            {"role": "agent", "text": "Absolutely. I've found the issue and I'm correcting it now — one moment."},
        ],
    },
]

_DETAILS: dict[str, dict[str, Any]] = {
    "cs-5": {
        "title": "customer-support · run #5",
        "sub": "customer_support_eval.py · gemini-2.0-flash · 2026-07-01 12:40 · 41s",
        "rate": 87.5, "status": "pass", "threshold": 80,
        "stats": [
            {"label": "cases", "value": "24"},
            {"label": "passed", "value": "21", "tone": "ok"},
            {"label": "failed", "value": "3", "tone": "bad"},
            {"label": "avg score", "value": "0.86"},
            {"label": "avg latency", "value": "1.8s"},
            {"label": "total cost", "value": "$0.11"},
        ],
        "cases": _CS5_CASES,
        "regression": {
            "note": {"current": "run #5 (87.5%)", "prev": "run #4 (91.7%)", "suite": "same suite"},
            "summary": [
                {"label": "pass-rate drift", "value": "-4.2pp", "tone": "bad"},
                {"label": "newly failing", "value": "2", "tone": "bad"},
                {"label": "newly passing", "value": "0", "tone": "ok"},
                {"label": "avg score drift", "value": "-0.03", "tone": "warn"},
            ],
            "rows": [
                {"name": "refuses out-of-policy refund", "delta": "0.81 → 0.62  ▼0.19", "dir": "down", "flip": "pass → fail", "stay": False},
                {"name": "handles unknown product SKU", "delta": "0.85 → 0.79  ▼0.06", "dir": "down", "flip": "pass → fail", "stay": False},
                {"name": "multi-turn: escalation to human", "delta": "0.71 → 0.71  —", "dir": "flat", "flip": "fail (same)", "stay": True},
                {"name": "refund within policy window", "delta": "0.84 → 0.88  ▲0.04", "dir": "up", "flip": "pass (same)", "stay": True},
            ],
        },
    },
}


def _detail_for(run_id: str) -> dict[str, Any]:
    """Return the drilldown for a run, synthesising a minimal one for runs that
    aren't fully populated so every list row stays selectable."""
    if run_id in _DETAILS:
        return _DETAILS[run_id]
    run = next((r for r in _RUNS if r["id"] == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Eval run '{run_id}' not found")
    passed = round(run["cases"] * run["rate"] / 100)
    return {
        "title": f"{run['name']} · run {run['run']}",
        "sub": f"{run['name']}_eval.py · {run['ago']}",
        "rate": run["rate"], "status": run["status"], "threshold": 80,
        "stats": [
            {"label": "cases", "value": str(run["cases"])},
            {"label": "passed", "value": str(passed), "tone": "ok"},
            {"label": "failed", "value": str(run["cases"] - passed), "tone": "bad"},
        ],
        "cases": [
            {
                "id": "c1", "name": "sample case", "type": "eval",
                "score": run["rate"] / 100, "status": run["status"],
                "lat": "1.5s", "cost": "$0.005",
                "input": "(summary only — full report not captured for this run)",
                "expected": "—", "actual": "—",
            }
        ],
        "regression": None,
    }


# --------------------------------------------------------------------------- #
#  Routes                                                                      #
# --------------------------------------------------------------------------- #


@router.get("/v1/evals/runs", summary="List eval runs")
async def list_eval_runs(request: Request):
    """List all eval runs (summary rows)."""
    return success_response({"runs": _RUNS}, request)


@router.get("/v1/evals/runs/{run_id}", summary="Get eval run detail")
async def get_eval_run(run_id: str, request: Request):
    """Return the full drilldown for one eval run."""
    return success_response(_detail_for(run_id), request)
