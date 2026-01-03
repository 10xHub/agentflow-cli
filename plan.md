# Dev Playground Plan for Agentflow CLI

## Summary ✅
Add a CLI feature (e.g., `agentflow api --open` or `agentflow dev`) that:
- Starts the development FastAPI server (uvicorn) on the selected host/port.
- Serves a simple interactive `playground` UI and any related static assets at `/playground`.
- Automatically opens a single browser window/tab to the `playground` URL when the server is ready.

This improves the developer DX by surfacing an interactive dev playground on `dev` runs in a single, consistent UX.

---

## Goals & Requirements 🎯
- Add a CLI flag to launch the playground automatically (default: opt-in: `--open` or `dev` default true).
- Serve a lightweight, local playground UI that calls the API endpoints.
- Ensure the browser opens only once when running the CLI (avoid multiple windows/tabs even while using `--reload`).
- Avoid opening browser in headless CI or tests.
- Keep default behavior unchanged (no production browser opens).

---

## Implementation Options (Pros & Cons) 🔧
Option A — Minimal (Recommended):
- Add `--open` flag to the existing `api` CLI command (or create an alias `dev`).
- Add a small static HTML/JS playground at `src/app/static/playground/index.html`.
- Add a FastAPI route `/playground` to serve the playground or configure `StaticFiles` middleware.
- Launch uvicorn programmatically via `uvicorn.Server` or start it in a background thread, and once the server responds to `/ping`, open `webbrowser.open(url)`. This avoids opening before the server is ready.

Pros: Direct, minimal, leverages existing FastAPI app and uvicorn.
Cons: Must ensure it doesn't open on reloader spawn; simple logic required to open only once.

Option B — Use Swagger / ReDoc (Quick & Safe):
- Reuse existing `docs_url` or `redoc_url` (e.g., open `/docs`).

Pros: No new routes or frontend required.
Cons: Not a custom playground UI.

Option C — Use a local `PyWebView` (Desktop app) or native webview.
- Spawn a desktop window embedding the playground. More complex and cross-platform issues.

Pros: Single top-level window without the browser.
Cons: Extra dependencies; not necessary for a simple developer experience.

---

## Technical Considerations and Constraints ⚠️
- Uvicorn reload behavior: when `--reload` is enabled it spawns a new server process on code changes. Opening the browser should happen only once, not on each worker spawn. Avoid re-opening by either:
  - Opening the browser from the CLI thread after the server responds (preferred). Or,
  - Use environment checks to ensure only the main process opens the browser.

- Polling for readiness: Use the `/ping` endpoint to perform a health check until the server responds (timeout e.g., 5s) then open the browser.

- Headless / CI environments: Skip opening the browser if `CI` or `GITHUB_ACTIONS` or `CI` env var is set, or if `DISPLAY` is not present (Linux headless) — allow opt-in overriding.

- Cross platform `webbrowser` support: the Python `webbrowser` module is cross-platform — use `webbrowser.open(url, new=0)`.

- Avoid opening multiple tabs/windows: Use the browser API `open(..., new=0)` to reuse an existing browser window where possible, and only call once.

- Security: Keep the playground local, do not expose sensitive resources; add guard to serve playground if `settings.MODE == "DEVELOPMENT"` or explicit config.

---

## CLI UX Design ✨
- Preferred command: `agentflow dev` (alias to `agentflow api --open`)
- Example usage:
  - `agentflow dev` — start dev server + open playground (default)
  - `agentflow api --open` — start server + open playground
  - `agentflow api` — start server without browser (existing behavior)
  - `agentflow dev --no-open` — start server without browser

Flags:
- `--open / --no-open` or `--playground / --no-playground`.
- `--host`, `--port`, `--reload` retain compatibility.

---

## Proposed Implementation Steps (High-level) 🛠️
1. Add CLI option and command alias
   - Add a new CLI `dev` command in `agentflow_cli/cli/commands/` as a thin wrapper around the existing `api` command or add `--open` flag to `APICommand.execute`.
   - Example: `agentflow_cli/cli/commands/api.py`: add `open_playground: bool = False` to signature.

2. Playground route & static assets
   - Add a new router `playground.router` in `src/app/routers` exposing `/playground`.
   - Add a `static` directory (e.g. `agentflow_cli/src/app/static/playground/`) with `index.html` and optionally `app.js` and CSS.
   - Use `FastAPI`'s `StaticFiles` or `HTMLResponse`/`Jinja2Templates` to serve.
   - Register the router conditionally when `settings.MODE == 'DEVELOPMENT'` or `settings.PLAYGROUND_ENABLED`.

3. Browser opening logic
   - Update `APICommand` to accept `open_playground`.
   - Option A (recommended): Launch the server programmatically: `uvicorn.Server(config)` in a thread, poll `http://host:port/ping` for readiness, then open the browser.
   - Option B: If staying with `uvicorn.run()` (blocking), we can start a small thread to poll and open the browser.

Example pseudo-code sketch:
```python
# inside APICommand.execute
if open_playground and not is_ci():
    url = f"http://{host}:{port}/playground"
    t = threading.Thread(target=_wait_and_open, args=(url, host, port), daemon=True)
    t.start()

uvicorn.run(...)

# helper
def _wait_and_open(url, host, port):
    for _ in range(50):
        try:
            r = requests.get(f"http://{host}:{port}/ping", timeout=0.5)
            if r.ok:
                webbrowser.open(url, new=0)
                return
        except Exception:
            time.sleep(0.1)

```

4. Unit tests
   - Mock `webbrowser.open` and `requests` to assert the open call when `--open` is used.
   - Mock `uvicorn.run` to avoid actually starting the server during unit tests.

5. Integration tests (optional)
   - Spin up app via `TestClient` or start a backward uvicorn instance, call `/playground` to ensure route returns `200`.

6. Documentation
   - Update `README.md` and `docs` describing `dev` command and how to use it.

---

## How to implement single-browser-session behavior (single tab) 🚪
- Use the `webbrowser`'s `new=0` value to attempt to reuse a window/tab.
- Add a small CLI-local sentinel — write the url or timestamp into a tempfile (e.g., `/tmp/agentflow_playground_{port}.txt`) and only open the browser if that sentinel is missing or stale (e.g., older than 15 seconds). This avoids re-opening on reload events.
- The sentinel approach isn't bulletproof but simplifies logic and avoids frequent reopens.

---

## Edge Cases & Tests 🧪
- CI environments: Should not open the browser. Detect CI by `CI` env var or skip/guard.
- Headless Linux: If `DISPLAY` is absent and not WSL, skip opening.
- `--reload` (dev reload): Avoid re-opening on each reload by keeping a sentinel or ensuring the open call fires only once.
- Port in use: If port in use, error should be returned gracefully.

---

## Acceptance Criteria ✅
- [ ] A `dev` command or `--open-playground` flag is present and documented.
- [ ] Launcher opens browser to `/playground` only once at initial start.
- [ ] Playground UI is served at `/playground` and works as expected (basic testing endpoints).
- [ ] CLI unit tests verify the browser open behavior (using mocking); integration tests verify route serves content.

---

## Optional Future Enhancements 💡
- Toggle auto-open link per environment variable or per `setup.cfg`/`settings` for developer preference.
- Build a more robust playground UI with OAuth injection or virtual keys (with caution).
- Option to open a standalone desktop playground (PyWebView) for native UX.

---

## Resources & Links (Research) 📚
- Python webbrowser: https://docs.python.org/3/library/webbrowser.html
- Uvicorn reload and process/child detection: https://www.uvicorn.org/
- Starting uvicorn programmatically: https://www.uvicorn.org/deployment/#programmatically
- FastAPI static files & HTML responses: https://fastapi.tiangolo.com/tutorial/static-files/
- Example implementations that open a browser on startup: many projects use `webbrowser.open` plus a health check.


---

## Next Steps (Implementation action list) 📝
- [ ] Add `open_playground` flag to `APICommand` (or add `dev` command).
- [ ] Add `playground` route & static files.
- [ ] Add readiness poll + `webbrowser.open` into CLI logic.
- [ ] Add unit tests for CLI open behavior and route tests for `/playground`.
- [ ] Document usage and examples in `README.md`.


---

Appendix: Example CLI usage
```bash
# Start the server and open playground (default on dev)
agentflow dev

# Start API server without opening browser
agentflow api --no-open

# Start API server and explicitly open
agentflow api --open
```

If you want, I can follow up by implementing a minimal PR that adds `--open` and a tiny `playground` route (HTML + small JS) and tests. Let me know which option you prefer (A: `dev` alias default true, B: `--open` opt-in for `api`), and I will start implementing it.