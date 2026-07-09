"""Reads real `agentflow eval` reports for the evals API.

Reports are written by `agentflow eval` (agentflow_cli/cli/commands/eval.py) via the core
`ReporterManager` / `JSONReporter` (agentflow/qa/evaluation/reporters/json.py) as
`eval_reports/*.json`, one file per run. That schema (`EvalReport` / `EvalCaseResult` /
`EvalSummary` in agentflow/qa/evaluation/eval_result.py) has no run-number, no dollar cost
(only token counts), no per-case "expected" value, and no built-in regression comparison
between runs — those are derived here so the response keeps the shape the playground's
Evals inspector already renders (see agentflow-playground/src/pages/evals/data.js).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException


DEFAULT_REPORTS_DIR = "eval_reports"
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
TOKENS_PER_KILO = 1000
REGRESSION_FLAT_EPSILON = 0.005


def _format_ago(timestamp: float, now: float) -> str:
    delta = max(0.0, now - timestamp)
    if delta < SECONDS_PER_MINUTE:
        return "just now"
    minutes = delta / SECONDS_PER_MINUTE
    if minutes < MINUTES_PER_HOUR:
        return f"{int(minutes)}m ago"
    hours = minutes / MINUTES_PER_HOUR
    if hours < HOURS_PER_DAY:
        return f"{int(hours)}h ago"
    days = hours / HOURS_PER_DAY
    return f"{int(days)}d ago"


def _format_duration(seconds: float) -> str:
    return f"{seconds:.1f}s"


def _format_tokens(token_usage: dict[str, Any] | None) -> str:
    total = (token_usage or {}).get("total_tokens", 0)
    if total >= TOKENS_PER_KILO:
        return f"{total / TOKENS_PER_KILO:.1f}k tok"
    return f"{total} tok"


def _case_type(case: dict[str, Any]) -> str:
    return "sim" if "turns" in (case.get("metadata") or {}) else "eval"


def _case_score(case: dict[str, Any]) -> float:
    criteria = case.get("criterion_results") or []
    if not criteria:
        return 1.0 if case.get("passed") else 0.0
    return sum(cr.get("score", 0.0) for cr in criteria) / len(criteria)


def _case_input(case: dict[str, Any]) -> str:
    for message in case.get("messages") or []:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content:
            return content
        if isinstance(content, list):
            texts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            if texts:
                return " ".join(texts)
    return "—"


def _case_conversation(case: dict[str, Any]) -> list[dict[str, str]] | None:
    if _case_type(case) != "sim":
        return None
    turns: list[dict[str, str]] = []
    for raw_line in (case.get("actual_response") or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("USER:"):
            turns.append({"role": "sim", "text": stripped[len("USER:") :].strip()})
        elif stripped.startswith("AGENT:"):
            turns.append({"role": "agent", "text": stripped[len("AGENT:") :].strip()})
        else:
            turns.append({"role": "agent", "text": stripped})
    return turns or None


def _case_rubric(case: dict[str, Any]) -> list[dict[str, Any]] | None:
    criteria = case.get("criterion_results") or []
    if not criteria:
        return None
    rubric = [
        {
            "key": cr.get("criterion", ""),
            "value": round(cr.get("score", 0.0), 2),
            "tone": "accent" if cr.get("passed") else "danger",
        }
        for cr in criteria
    ]
    rubric.append(
        {
            "key": "weighted score",
            "value": round(_case_score(case), 2),
            "tone": "accent" if case.get("passed") else "danger",
        }
    )
    return rubric


def _build_case_view(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case.get("eval_id", ""),
        "name": case.get("name") or case.get("eval_id", ""),
        "type": _case_type(case),
        "score": round(_case_score(case), 2),
        "status": "pass" if case.get("passed") else "fail",
        "lat": _format_duration(case.get("duration_seconds", 0.0)),
        "cost": _format_tokens(case.get("token_usage")),
        "input": _case_input(case),
        "expected": "—",
        "actual": case.get("actual_response") or "—",
        "rubric": _case_rubric(case),
        "conversation": _case_conversation(case),
    }


def _run_status(report: dict[str, Any]) -> str:
    return "pass" if report.get("summary", {}).get("pass_rate", 0.0) >= 1.0 else "fail"


def _derive_threshold(report: dict[str, Any]) -> float:
    thresholds = {
        cr.get("threshold", 0.0)
        for case in report.get("results", [])
        for cr in case.get("criterion_results", [])
    }
    if not thresholds:
        return 80.0
    return round(100 * sum(thresholds) / len(thresholds))


def _build_stats(report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = report.get("summary", {})
    cases = report.get("results", [])
    scores = [_case_score(c) for c in cases]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    return [
        {"label": "cases", "value": str(summary.get("total_cases", 0))},
        {"label": "passed", "value": str(summary.get("passed_cases", 0)), "tone": "ok"},
        {
            "label": "failed",
            "value": str(summary.get("failed_cases", 0) + summary.get("error_cases", 0)),
            "tone": "bad",
        },
        {"label": "avg score", "value": f"{avg_score:.2f}"},
        {
            "label": "avg latency",
            "value": _format_duration(summary.get("avg_duration_seconds", 0.0)),
        },
        {"label": "total tokens", "value": _format_tokens(summary.get("total_token_usage"))},
    ]


def _build_run_row(
    report: dict[str, Any], run_id: str, run_label: str, now: float
) -> dict[str, Any]:
    summary = report.get("summary", {})
    return {
        "id": run_id,
        "name": report.get("eval_set_name") or report.get("eval_set_id", ""),
        "run": run_label,
        "rate": round(summary.get("pass_rate", 0.0) * 100, 1),
        "status": _run_status(report),
        "cases": summary.get("total_cases", 0),
        "ago": _format_ago(report.get("timestamp", now), now),
    }


def _build_regression(
    current: dict[str, Any],
    current_label: str,
    previous: dict[str, Any],
    previous_label: str,
) -> dict[str, Any]:
    cur_cases = {c["eval_id"]: c for c in current.get("results", [])}
    prev_cases = {c["eval_id"]: c for c in previous.get("results", [])}

    rows: list[dict[str, Any]] = []
    newly_failing = 0
    newly_passing = 0
    for eval_id, cur_case in cur_cases.items():
        prev_case = prev_cases.get(eval_id)
        if prev_case is None:
            continue
        cur_score = _case_score(cur_case)
        prev_score = _case_score(prev_case)
        delta = cur_score - prev_score

        if prev_case["passed"] and not cur_case["passed"]:
            newly_failing += 1
            flip = "pass → fail"
        elif not prev_case["passed"] and cur_case["passed"]:
            newly_passing += 1
            flip = "fail → pass"
        else:
            flip = f"{'pass' if cur_case['passed'] else 'fail'} (same)"

        if abs(delta) < REGRESSION_FLAT_EPSILON:
            dir_, arrow = "flat", "—"
        elif delta > 0:
            dir_, arrow = "up", f"▲{delta:.2f}"
        else:
            dir_, arrow = "down", f"▼{abs(delta):.2f}"

        rows.append(
            {
                "name": cur_case.get("name") or eval_id,
                "delta": f"{prev_score:.2f} → {cur_score:.2f}  {arrow}",
                "dir": dir_,
                "flip": flip,
                "stay": cur_case["passed"] == prev_case["passed"],
            }
        )

    cur_rate = current.get("summary", {}).get("pass_rate", 0.0) * 100
    prev_rate = previous.get("summary", {}).get("pass_rate", 0.0) * 100
    cur_scores = [_case_score(c) for c in current.get("results", [])]
    prev_scores = [_case_score(c) for c in previous.get("results", [])]
    avg_cur = sum(cur_scores) / len(cur_scores) if cur_scores else 0.0
    avg_prev = sum(prev_scores) / len(prev_scores) if prev_scores else 0.0
    score_drift = avg_cur - avg_prev
    rate_drift = cur_rate - prev_rate

    return {
        "note": {
            "current": f"run {current_label} ({cur_rate:.1f}%)",
            "prev": f"run {previous_label} ({prev_rate:.1f}%)",
            "suite": "same suite",
        },
        "summary": [
            {
                "label": "pass-rate drift",
                "value": f"{rate_drift:+.1f}pp",
                "tone": "bad" if rate_drift < 0 else "ok",
            },
            {
                "label": "newly failing",
                "value": str(newly_failing),
                "tone": "bad" if newly_failing else "ok",
            },
            {"label": "newly passing", "value": str(newly_passing), "tone": "ok"},
            {
                "label": "avg score drift",
                "value": f"{score_drift:+.2f}",
                "tone": "warn" if score_drift < 0 else "ok",
            },
        ],
        "rows": rows,
    }


class EvalReportService:
    """Reads `eval_reports/*.json` and adapts them into the run/detail shape
    the playground's Evals inspector expects."""

    def __init__(self, reports_dir: str | Path | None = None) -> None:
        base = Path(reports_dir) if reports_dir is not None else Path(DEFAULT_REPORTS_DIR)
        self.reports_dir = base if base.is_absolute() else Path.cwd() / base

    def _load_reports(self) -> list[tuple[str, dict[str, Any]]]:
        if not self.reports_dir.is_dir():
            return []
        reports = []
        for path in sorted(self.reports_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            reports.append((path.stem, data))
        reports.sort(key=lambda item: item[1].get("timestamp", 0.0))
        return reports

    def _run_labels(self) -> dict[str, tuple[int, dict[str, Any], str | None]]:
        """run_id -> (run_number, report, previous_run_id), run_number and
        previous_run_id computed per eval_set_id in chronological order."""
        counters: dict[str, int] = {}
        previous_by_name: dict[str, str] = {}
        labels: dict[str, tuple[int, dict[str, Any], str | None]] = {}
        for run_id, report in self._load_reports():
            name = report.get("eval_set_id", "")
            counters[name] = counters.get(name, 0) + 1
            labels[run_id] = (counters[name], report, previous_by_name.get(name))
            previous_by_name[name] = run_id
        return labels

    def list_runs(self, now: float | None = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        labels = self._run_labels()
        rows = [
            (report.get("timestamp", 0.0), _build_run_row(report, run_id, f"#{run_number}", now))
            for run_id, (run_number, report, _prev) in labels.items()
        ]
        rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in rows]

    def get_run_detail(self, run_id: str) -> dict[str, Any]:
        labels = self._run_labels()
        entry = labels.get(run_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Eval run '{run_id}' not found")
        run_number, report, previous_run_id = entry
        summary = report.get("summary", {})

        regression = None
        if previous_run_id is not None:
            prev_entry = labels.get(previous_run_id)
            if prev_entry is not None:
                prev_number, prev_report, _ = prev_entry
                regression = _build_regression(
                    report, f"#{run_number}", prev_report, f"#{prev_number}"
                )

        model = (report.get("config_used") or {}).get("model")
        run_timestamp = time.gmtime(report.get("timestamp", 0.0))
        sub_parts = [report.get("eval_set_id", "")]
        if model:
            sub_parts.append(str(model))
        sub_parts.append(time.strftime("%Y-%m-%d %H:%M", run_timestamp))
        sub_parts.append(_format_duration(summary.get("total_duration_seconds", 0.0)))

        set_label = report.get("eval_set_name") or report.get("eval_set_id", "")
        return {
            "title": f"{set_label} · run #{run_number}",
            "sub": " · ".join(sub_parts),
            "rate": round(summary.get("pass_rate", 0.0) * 100, 1),
            "status": _run_status(report),
            "threshold": _derive_threshold(report),
            "stats": _build_stats(report),
            "cases": [_build_case_view(c) for c in report.get("results", [])],
            "regression": regression,
        }
