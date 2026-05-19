# Agentflow Evaluation CLI & Report Improvement Plan

## Overview

Three goals:
1. Add `agentflow test` CLI command — run pytest for the project's `tests/` directory
2. Add `agentflow eval` CLI command — discover and run evaluations from `evals/`
3. Improve the HTML evaluation report to be a proper dashboard

---

## Part 1: `agentflow test` Command

### What it does
Runs pytest inside the user's project directory. Thin wrapper around pytest subprocess with sensible defaults and a pretty Typer UI.

### Behavior
```
agentflow test                     # runs tests/ with -v
agentflow test --coverage          # adds --cov=. --cov-report=html
agentflow test --path tests/unit   # target specific path
agentflow test --html              # open HTML coverage report after run
agentflow test -k "weather"        # pass -k to pytest
agentflow test -- --no-header -q   # pass raw args after --
```

### Implementation

**File**: `agentflow-api/agentflow_cli/cli/commands/test.py`

```python
class TestCommand(BaseCommand):
    def __init__(self, path, coverage, html, extra_args, verbose, quiet):
        ...

    def execute(self) -> int:
        cmd = ["python", "-m", "pytest", self.path, "-v"]
        if self.coverage:
            cmd += ["--cov=.", "--cov-report=term-missing", "--cov-report=html:htmlcov"]
        cmd += list(self.extra_args)

        result = subprocess.run(cmd, cwd=self.project_root)

        if self.html and self.coverage:
            webbrowser.open(f"htmlcov/index.html")

        return result.returncode
```

**Registration in `main.py`**:
```python
@app.command()
def test(
    path: str = typer.Argument("tests", help="Path to tests directory"),
    coverage: bool = typer.Option(False, "--coverage", "-C", help="Run with coverage"),
    html: bool = typer.Option(False, "--html", help="Open HTML coverage report after run"),
    keyword: str = typer.Option(None, "-k", help="Only run tests matching this expression"),
    verbose: bool = ...,
    quiet: bool = ...,
    extra: list[str] = typer.Argument(None),
):
    """Run project tests with pytest."""
```

**`agentflow.json` addition** (optional override):
```json
{
  "test": {
    "path": "tests",
    "coverage": true,
    "coverage_threshold": 70
  }
}
```

---

## Part 2: `agentflow eval` Command

### What it does
Discovers evaluation modules in a directory, runs them, and always generates HTML + JSON reports. Reports are on by default; the user can disable them explicitly.

### Behavior
```
agentflow eval                             # auto-discover evals/ → always generates report
agentflow eval evals/weather_agents.py     # run a single file → still generates report
agentflow eval evals/                      # run a specific folder
agentflow eval --output eval_reports       # override output directory
agentflow eval --no-report                 # skip report generation (console only)
agentflow eval --threshold 0.8             # fail if pass rate < 80%
agentflow eval --open                      # open HTML report in browser after run
```

Key rules:
- **Report generation is always on.** Every run writes `eval_reports/report_<timestamp>.html` and `eval_reports/report_<timestamp>.json` plus prints to console.
- The first positional argument is optional: a file path or a directory. If omitted, the command auto-discovers from `evals/` (or `agentflow.json` `"evaluation.directory"`).
- `--no-report` is the only way to suppress file output. Console output is always shown.
- `--open` opens the HTML file in the default browser after a successful run.

### Auto-Discovery Protocol

When a directory is given (or defaulted), the command scans it recursively for Python files matching `*_eval.py` or `eval_*.py`. Each file must expose a callable with one of these signatures:

```python
# Option A: a function named `get_eval_config` (preferred)
def get_eval_config() -> EvalConfig:
    ...

# Option B: a top-level constant `EVAL_CONFIG`
EVAL_CONFIG = EvalConfig(...)

# Option C: a function named `run` (for full control)
async def run() -> EvalReport:
    ...
```

**No decorator needed.** Convention > registration. The CLI introspects the module and picks the first matching symbol. Files with none of the above are skipped with a warning.

### `agentflow.json` Integration

Add an `"evaluation"` key (all fields optional):

```json
{
  "evaluation": {
    "directory": "evals",
    "output_dir": "eval_reports",
    "threshold": 0.75,
    "timestamp_files": true
  }
}
```

If absent, defaults apply: `evals/`, `eval_reports/`, no threshold, timestamped files on. The `formats` field is removed — html + json + console are always generated; `--no-report` disables file output entirely rather than letting users mix and match.

### Implementation

**File**: `agentflow-api/agentflow_cli/cli/commands/eval.py`

```python
class EvalCommand(BaseCommand):
    async def _run_file(self, path: Path) -> EvalReport | None:
        spec = importlib.util.spec_from_file_location("_eval_module", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if hasattr(mod, "get_eval_config"):
            config: EvalConfig = mod.get_eval_config()
            agent = self._load_agent()
            runner = EvaluationRunner(agent, config)
            return await runner.run()

        elif hasattr(mod, "EVAL_CONFIG"):
            config: EvalConfig = mod.EVAL_CONFIG
            agent = self._load_agent()
            runner = EvaluationRunner(agent, config)
            return await runner.run()

        elif hasattr(mod, "run"):
            return await mod.run()

        else:
            self.warn(f"No eval entry point found in {path}, skipping")
            return None

    def _discover(self, target: Path) -> list[Path]:
        if target.is_file():
            return [target]
        return sorted(target.rglob("*_eval.py")) + sorted(target.rglob("eval_*.py"))

    def execute(self) -> int:
        reports = asyncio.run(self._run_all())
        if not reports:
            self.error("No eval reports produced.")
            return 1

        merged = merge_reports(reports)
        print_report(merged)

        if not self.no_report:
            manager = ReporterManager(ReporterConfig(
                output_dir=self.output_dir,
                html=True,
                json=True,
                timestamp_files=True,
            ))
            result = manager.run_all(merged)
            self.info(f"Report saved: {result.html_path}")
            if self.open_report and result.html_path:
                webbrowser.open(result.html_path)

        return 0 if merged.passed else 1
```

**Registration in `main.py`**:
```python
@app.command()
def eval(
    target: Optional[str] = typer.Argument(None, help="File or directory to evaluate (default: evals/)"),
    output_dir: str = typer.Option("eval_reports", "--output", "-o", help="Report output directory"),
    no_report: bool = typer.Option(False, "--no-report", help="Skip file report generation"),
    threshold: float = typer.Option(None, "--threshold", "-t", help="Fail if pass rate below this value"),
    open_report: bool = typer.Option(False, "--open", help="Open HTML report in browser after run"),
    verbose: bool = ...,
    quiet: bool = ...,
):
    """Run agent evaluations. Always generates HTML + JSON reports unless --no-report is set."""
```

### `evals/` Template Update

The `prod` init template's `evals/weather_agents.py` needs a `get_eval_config()` export added:

```python
def get_eval_config() -> EvalConfig:
    return build_weather_agent_eval_config()
```

That is the only change needed to make existing eval files CLI-discoverable.

---

## Part 3: HTML Report Redesign

### Problems with Current Report
- Single inline template string (hard to maintain)
- No charts — pass/fail is just text
- No dark mode
- Case items are plain `<div>` toggles with no visual hierarchy
- No score trend / criterion breakdown chart
- Criteria listed as text, not visual scores

### Target Design

A self-contained single HTML file (no external CDN, all JS/CSS inlined) with:

```
┌─────────────────────────────────────────────────────────┐
│  AgentFlow Eval Report          [timestamp] [dark toggle]│
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  12/15   │ │  80.0%   │ │  8 Pass  │ │  4 Fail  │  │
│  │  Cases   │ │ Pass Rate│ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├───────────────────────┬─────────────────────────────────┤
│  Criterion Breakdown  │  Pass Rate by Case (bar chart)  │
│  (horizontal bars)    │                                 │
├───────────────────────┴─────────────────────────────────┤
│  [All] [Pass] [Fail] [Error]    🔍 Search cases         │
├─────────────────────────────────────────────────────────┤
│  ▶ weather_london          ✓ PASS   Score: 0.95  100ms  │
│  ▼ weather_new_york        ✗ FAIL   Score: 0.40  230ms  │
│    ┌── Agent Response ─────────────────────────────┐    │
│    │  "The weather in New York is..."              │    │
│    └───────────────────────────────────────────────┘    │
│    ┌── Criteria ───────────────────────────────────┐    │
│    │  tool_name_match   ████████░░  0.8  ✓        │    │
│    │  response_match    ████░░░░░░  0.4  ✗        │    │
│    └───────────────────────────────────────────────┘    │
│    ┌── Trajectory ─────────────────────────────────┐    │
│    │  TOOL_CALL → get_weather({location: "NY"})   │    │
│    │  RESPONSE  → "The weather..."                │    │
│    └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Technical Approach

**Keep it a single self-contained HTML string** (no external files). Split the Python template into logical sections:

```
reporters/
├── html.py            # HTMLReporter class (orchestrator, stays small)
├── _html_template.py  # HTML_TEMPLATE string (head + body structure)
├── _html_css.py       # CSS_CONTENT string (full stylesheet)
├── _html_js.py        # JS_CONTENT string (charts + interactivity)
└── _html_render.py    # _render_case(), _render_criterion(), etc.
```

`html.py` assembles them at `to_html()` time:
```python
HTML_TEMPLATE = HEAD + BODY_OPEN + CHART_SCRIPTS + BODY_CLOSE
# All CSS/JS are written inline into <style> and <script> tags
```

### Chart Implementation (no CDN)

Use a minimal inline SVG-based bar chart renderer written in vanilla JS (~80 lines). No Chart.js dependency. The JS reads `data-pass`, `data-score` attributes from rendered HTML and draws `<svg>` charts client-side.

### New CSS Features
- CSS custom properties supporting both light and dark themes
- `prefers-color-scheme: dark` media query + manual toggle button
- `grid` layout for summary cards
- `transition` on expand/collapse
- Score bars as CSS `width: calc(score * 100%)` with color interpolation (green → red)
- `position: sticky` header with filter controls

### Criterion Score Bar (inline)
```html
<div class="criterion-row">
  <span class="criterion-name">tool_name_match</span>
  <div class="score-bar">
    <div class="score-fill" style="width: 80%; background: hsl(142, 72%, 45%)"></div>
  </div>
  <span class="score-value">0.80</span>
  <span class="criterion-status pass">✓</span>
</div>
```

---

## Implementation Order

| Step | Task | File(s) | Effort |
|------|------|---------|--------|
| 1 | `agentflow test` command | `commands/test.py`, `main.py` | Small |
| 2 | Add `test` key to `ConfigManager` | `core/config.py` | Small |
| 3 | HTML CSS/JS refactor — split template | `reporters/_html_*.py` | Medium |
| 4 | Criterion score bars + dark mode | `reporters/_html_css.py` | Medium |
| 5 | Inline SVG chart renderer | `reporters/_html_js.py` | Medium |
| 6 | `agentflow eval` command + auto-discovery | `commands/eval.py`, `main.py` | Medium |
| 7 | `evaluation` key in `ConfigManager` | `core/config.py` | Small |
| 8 | Add `get_eval_config()` to prod template | `templates/prod/evals/weather_agents.py` | Tiny |
| 9 | Unit tests for eval command discovery | `tests/` | Medium |

---

## Key Decisions

### Why convention over registration?
`@register_eval` decorators require importing the module at registration time, which pulls in user's `graph.agent`, LLM clients, etc. — expensive and fragile in the CLI context. Convention-based discovery (`get_eval_config()` / `EVAL_CONFIG`) lets the CLI import the module lazily and resolve the agent from `agentflow.json` independently.

### Why not add eval to `agentflow.json` as required?
The `evals/` convention works without any config. The optional `"evaluation"` key in `agentflow.json` is only needed for non-standard paths or threshold overrides — keeps it zero-config by default.

### Why keep the HTML self-contained?
Users share `report.html` files. CDN dependencies break in offline environments. All CSS + JS stays inlined.

### Why split the Python template strings?
`reporters/html.py` is already hundreds of lines. Splitting into `_html_css.py`, `_html_js.py`, `_html_template.py`, `_html_render.py` makes each file focused and reviewable without changing the public `HTMLReporter` API.
