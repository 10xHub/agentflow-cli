# Action Plan: Unified Dev Server Command

## Overview

Create an `agentflow dev` CLI command that runs both the **API server** and **UI dashboard** together, providing a seamless development experience. The UI will consume the API using the existing TypeScript SDK (`@10xscale/agentflow-client`).

---

## Current Architecture

### 1. CLI (pyagenity-api)
- **Entry point**: `agentflow_cli/cli/main.py`
- **Commands**: `api`, `init`, `build`, `version`
- **API Server**: FastAPI app at `agentflow_cli/src/app/main.py`
- **Default ports**: API on `127.0.0.1:8000`

### 2. UI (pyagenity-ui)
- **Framework**: React 19 + Vite
- **API Integration**: Axios-based client reading `backendUrl` from localStorage
- **Dev server**: `npm run dev` (Vite on port 5173)
- **Build output**: `dist/` folder with static assets

### 3. TypeScript SDK (agentflow-react)
- **Package**: `@10xscale/agentflow-client`
- **Features**: Thread management, streaming, memory, tool execution
- **Client**: `AgentFlowClient` class with full API coverage

---

## Goal: `agentflow dev` Command

```bash
# Primary usage
agentflow dev                     # Start API + UI, auto-open browser

# With options
agentflow dev --port 8000         # Custom API port
agentflow dev --ui-port 5173      # Custom UI port
agentflow dev --no-open           # Don't open browser
agentflow dev --api-only          # Only start API (existing behavior)
```

---

## Implementation Phases

### Phase 1: Bundle UI into CLI Package

#### 1.1 Build and Package UI Assets

**Location**: `agentflow_cli/src/app/static/ui/`

**Steps**:
1. Add build script to build pyagenity-ui and copy to CLI package
2. Create a Makefile target or Python script for bundling:

```python
# scripts/bundle_ui.py
"""
Build the React UI and copy to CLI static directory.
"""
import subprocess
import shutil
from pathlib import Path

UI_SOURCE = Path("../pyagenity-ui")
UI_DEST = Path("agentflow_cli/src/app/static/ui")

def bundle_ui():
    # Build UI
    subprocess.run(["npm", "run", "build"], cwd=UI_SOURCE, check=True)

    # Clear destination
    if UI_DEST.exists():
        shutil.rmtree(UI_DEST)

    # Copy build output
    shutil.copytree(UI_SOURCE / "dist", UI_DEST)

    print(f"✅ UI bundled to {UI_DEST}")

if __name__ == "__main__":
    bundle_ui()
```

#### 1.2 Configure MANIFEST.in

Add to `MANIFEST.in`:
```
recursive-include agentflow_cli/src/app/static *
```

#### 1.3 Update pyproject.toml

```toml
[tool.setuptools.package-data]
"*" = ["*.json", "*.yaml", "*.yml", "*.md", "*.txt", "*.html", "*.js", "*.css", "*.svg", "*.png", "*.ico"]
```

---

### Phase 2: Create UI Router for FastAPI

**File**: `agentflow_cli/src/app/routers/ui/router.py`

```python
"""UI static file serving router."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

router = APIRouter()

# Path to bundled UI assets
UI_STATIC_DIR = Path(__file__).parent.parent.parent / "static" / "ui"


def get_ui_router():
    """Create router for serving UI static files."""
    router = APIRouter(tags=["UI"])

    @router.get("/")
    async def serve_ui_index():
        """Serve the main UI index.html."""
        index_path = UI_STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "UI not bundled. Run 'make bundle-ui' first."}

    return router


def mount_ui_static(app):
    """Mount static files for UI assets."""
    if UI_STATIC_DIR.exists():
        # Mount assets directory
        assets_dir = UI_STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="ui-assets")

        # Mount root static files (favicon, etc.)
        app.mount("/static", StaticFiles(directory=UI_STATIC_DIR), name="ui-static")
```

---

### Phase 3: Implement Dev Command

#### 3.1 Create Dev Command Class

**File**: `agentflow_cli/cli/commands/dev.py`

```python
"""Dev server command - runs API and UI together."""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import DEFAULT_CONFIG_FILE, DEFAULT_HOST, DEFAULT_PORT
from agentflow_cli.cli.core.config import ConfigManager
from agentflow_cli.cli.core.validation import validate_cli_options
from agentflow_cli.cli.exceptions import ConfigurationError, ServerError


DEFAULT_UI_PORT = 5173


class DevCommand(BaseCommand):
    """Command to start unified dev server with API and UI."""

    def execute(
        self,
        config: str = DEFAULT_CONFIG_FILE,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        ui_port: int = DEFAULT_UI_PORT,
        reload: bool = True,
        open_browser: bool = True,
        api_only: bool = False,
        **kwargs: Any,
    ) -> int:
        """Execute the dev server command.

        Args:
            config: Path to config file
            host: Host to bind to
            port: Port for API server
            ui_port: Port for UI server (if separate)
            reload: Enable auto-reload
            open_browser: Open browser on startup
            api_only: Only start API (no UI)
            **kwargs: Additional arguments

        Returns:
            Exit code
        """
        try:
            # Print banner
            self.output.print_banner(
                "Development Server",
                "Starting API" + ("" if api_only else " + UI Dashboard"),
            )

            # Validate inputs
            validated_options = validate_cli_options(host, port, config)

            # Load configuration
            config_manager = ConfigManager()
            actual_config_path = config_manager.find_config_file(validated_options["config"])
            config_manager.load_config(str(actual_config_path))

            # Load environment
            env_file_path = config_manager.resolve_env_file()
            if env_file_path:
                self.logger.info("Loading environment from: %s", env_file_path)
                load_dotenv(env_file_path)
            else:
                load_dotenv()

            # Set environment variables
            os.environ["GRAPH_PATH"] = str(actual_config_path)
            os.environ["AGENTFLOW_DEV_MODE"] = "1"
            os.environ["AGENTFLOW_UI_ENABLED"] = "0" if api_only else "1"

            # Ensure module path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            self.logger.info(
                "Starting dev server - API: %s:%d",
                validated_options["host"],
                validated_options["port"],
            )

            # Open browser after server starts
            if open_browser and not self._is_ci_environment():
                url = f"http://{host}:{port}"
                threading.Thread(
                    target=self._wait_and_open_browser,
                    args=(url, host, port),
                    daemon=True
                ).start()

            # Start the server
            uvicorn.run(
                "agentflow_cli.src.app.main:app",
                host=validated_options["host"],
                port=validated_options["port"],
                reload=reload,
                workers=1,
            )

            return 0

        except (ConfigurationError, ServerError) as e:
            return self.handle_error(e)
        except Exception as e:
            server_error = ServerError(
                f"Failed to start dev server: {e}",
                host=host,
                port=port,
            )
            return self.handle_error(server_error)

    def _wait_and_open_browser(self, url: str, host: str, port: int):
        """Wait for server readiness and open browser."""
        import requests

        ping_url = f"http://{host}:{port}/ping"

        for _ in range(50):  # 5 seconds max
            try:
                r = requests.get(ping_url, timeout=0.5)
                if r.ok:
                    webbrowser.open(url, new=0)
                    self.logger.info("Opened browser at %s", url)
                    return
            except Exception:
                time.sleep(0.1)

        self.logger.warning("Could not open browser - server not ready")

    def _is_ci_environment(self) -> bool:
        """Check if running in CI environment."""
        ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"]
        return any(os.environ.get(var) for var in ci_vars)
```

#### 3.2 Register Dev Command in Main CLI

**Update**: `agentflow_cli/cli/main.py`

```python
# Add import
from agentflow_cli.cli.commands.dev import DevCommand

# Add command
@app.command()
def dev(
    config: str = typer.Option(
        DEFAULT_CONFIG_FILE,
        "--config",
        "-c",
        help="Path to config file",
    ),
    host: str = typer.Option(
        DEFAULT_HOST,
        "--host",
        "-H",
        help="Host to run the server on",
    ),
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port for API server",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Open browser on startup",
    ),
    api_only: bool = typer.Option(
        False,
        "--api-only",
        help="Only start API server (no UI)",
    ),
    reload: bool = typer.Option(
        True,
        "--reload/--no-reload",
        help="Enable auto-reload for development",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
) -> None:
    """Start development server with API and UI dashboard."""
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = DevCommand(output)
        exit_code = command.execute(
            config=config,
            host=host,
            port=port,
            reload=reload,
            open_browser=open_browser,
            api_only=api_only,
        )
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))
```

---

### Phase 4: Update FastAPI App for UI Serving

**Update**: `agentflow_cli/src/app/main.py`

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(...)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount UI if in dev mode and UI is enabled
if os.environ.get("AGENTFLOW_UI_ENABLED") == "1":
    from agentflow_cli.src.app.routers.ui.router import get_ui_router, mount_ui_static

    # Mount static files first
    mount_ui_static(app)

    # Add UI routes (for SPA fallback)
    app.include_router(get_ui_router())
```

---

### Phase 5: Configure UI for Integrated Mode

#### 5.1 Update UI Build Configuration

**Update**: `pyagenity-ui/vite.config.js`

```javascript
export default defineConfig({
  // ... existing config

  base: '/',  // Serve from root

  build: {
    outDir: 'dist',
    // Generate assets with predictable names for bundling
    rollupOptions: {
      output: {
        // Keep asset names consistent
        assetFileNames: 'assets/[name].[hash][extname]',
        chunkFileNames: 'assets/[name].[hash].js',
        entryFileNames: 'assets/[name].[hash].js',
      },
    },
  },
})
```

#### 5.2 Auto-configure Backend URL

**Update**: `pyagenity-ui/src/services/api/index.js`

```javascript
// Auto-detect backend URL when served from same origin
const getDefaultBackendUrl = () => {
  // Check if we're running in integrated mode (same origin as API)
  if (window.location.pathname === '/' || window.location.pathname.startsWith('/')) {
    // Same origin - use current host
    return window.location.origin
  }

  // Fallback to localStorage
  return localStorage.getItem("backendUrl")
}

const instance = axios.create({
  timeout: 600000,
})

instance.interceptors.request.use(
  (request) => {
    try {
      // Use auto-detected URL or localStorage
      const backendUrl = localStorage.getItem("backendUrl") || getDefaultBackendUrl()

      if (backendUrl == null) {
        throw new Error("Backend URL is not set")
      }

      // ... rest of interceptor
    } catch (error) {
      return Promise.reject(error)
    }
    return request
  }
)
```

---

### Phase 6: Add Makefile Targets

**Update**: `pyagenity-api/Makefile`

```makefile
# ... existing targets

.PHONY: bundle-ui
bundle-ui:
	@echo "Building UI..."
	cd ../pyagenity-ui && npm install && npm run build
	@echo "Copying to CLI package..."
	rm -rf agentflow_cli/src/app/static/ui
	mkdir -p agentflow_cli/src/app/static/ui
	cp -r ../pyagenity-ui/dist/* agentflow_cli/src/app/static/ui/
	@echo "✅ UI bundled successfully"

.PHONY: dev
dev:
	uv run agentflow dev

.PHONY: dev-api-only
dev-api-only:
	uv run agentflow dev --api-only

.PHONY: install-dev
install-dev:
	uv sync
	make bundle-ui

.PHONY: build-release
build-release: bundle-ui
	uv build
```

---

### Phase 7: Testing Strategy

#### 7.1 Unit Tests

**File**: `tests/test_dev_command.py`

```python
"""Tests for dev command."""
import pytest
from unittest.mock import patch, MagicMock

from agentflow_cli.cli.commands.dev import DevCommand
from agentflow_cli.cli.core.output import OutputFormatter


class TestDevCommand:
    """Test DevCommand class."""

    def test_is_ci_environment_github(self):
        """Test CI detection for GitHub Actions."""
        cmd = DevCommand(OutputFormatter())
        with patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}):
            assert cmd._is_ci_environment() is True

    def test_is_ci_environment_not_ci(self):
        """Test CI detection when not in CI."""
        cmd = DevCommand(OutputFormatter())
        with patch.dict("os.environ", {}, clear=True):
            assert cmd._is_ci_environment() is False

    @patch("webbrowser.open")
    @patch("requests.get")
    def test_wait_and_open_browser(self, mock_get, mock_open):
        """Test browser opening logic."""
        mock_get.return_value = MagicMock(ok=True)

        cmd = DevCommand(OutputFormatter())
        cmd._wait_and_open_browser("http://localhost:8000", "localhost", 8000)

        mock_open.assert_called_once_with("http://localhost:8000", new=0)
```

#### 7.2 Integration Tests

**File**: `tests/test_ui_router.py`

```python
"""Tests for UI router."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


class TestUIRouter:
    """Test UI serving functionality."""

    def test_ui_assets_served(self, client: TestClient):
        """Test that UI assets are served correctly."""
        # This test requires UI to be bundled
        pass

    def test_spa_fallback(self, client: TestClient):
        """Test SPA routing fallback."""
        pass
```

---

### Phase 8: Documentation

#### 8.1 Update README.md

Add section:

```markdown
## Development Server

Start the unified development server with both API and UI:

```bash
# Start dev server (API + UI)
agentflow dev

# Start with custom port
agentflow dev --port 9000

# Start API only (existing behavior)
agentflow dev --api-only

# Don't auto-open browser
agentflow dev --no-open
```

The development server:
- Runs the FastAPI backend on the specified port (default: 8000)
- Serves the React UI dashboard at the root URL
- Auto-opens your browser to the dashboard
- Supports hot reload for API changes
```

---

## File Structure After Implementation

```
agentflow_cli/
├── cli/
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── build.py
│   │   ├── dev.py          # NEW
│   │   ├── init.py
│   │   └── version.py
│   └── main.py             # UPDATED
├── src/
│   └── app/
│       ├── main.py         # UPDATED
│       ├── routers/
│       │   ├── ui/         # NEW
│       │   │   ├── __init__.py
│       │   │   └── router.py
│       │   └── ...
│       └── static/
│           └── ui/         # NEW (bundled from pyagenity-ui)
│               ├── index.html
│               └── assets/
│                   ├── index-[hash].js
│                   └── index-[hash].css
├── Makefile                # UPDATED
├── MANIFEST.in             # UPDATED
└── pyproject.toml          # UPDATED
```

---

## Implementation Order

1. **Phase 1**: Bundle UI into CLI package (scripts, manifest, pyproject)
2. **Phase 2**: Create UI router for FastAPI
3. **Phase 3**: Implement DevCommand class
4. **Phase 4**: Update FastAPI main app for UI serving
5. **Phase 5**: Configure UI for integrated mode
6. **Phase 6**: Add Makefile targets
7. **Phase 7**: Write tests
8. **Phase 8**: Documentation

---

## Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    # ... existing
    "requests",  # For health check in dev command (if not already present)
]
```

---

## Success Criteria

- [ ] `agentflow dev` starts API server
- [ ] UI is served at root URL (`http://localhost:8000/`)
- [ ] Browser auto-opens to dashboard
- [ ] API endpoints remain accessible (`/ping`, `/graph/*`, etc.)
- [ ] Hot reload works for API changes
- [ ] `--api-only` flag works for API-only mode
- [ ] `--no-open` flag prevents browser opening
- [ ] UI can successfully communicate with API (same origin, no CORS issues)
- [ ] SDK (`@10xscale/agentflow-client`) works with the integrated server
- [ ] Build/release process includes bundled UI

---

## Notes

### Why Bundle UI Instead of Running Separate Vite Dev Server?

1. **Single port**: Everything runs on one port, avoiding CORS complexity
2. **Simple deployment**: One package to distribute
3. **Consistent experience**: Same behavior in dev and production
4. **No Node.js requirement**: Users only need Python to run dev server

### Alternative: Proxy Mode

If hot-reload for UI is needed during UI development:

```bash
# Terminal 1: API
agentflow dev --api-only

# Terminal 2: UI with proxy
cd ../pyagenity-ui
npm run dev  # Vite dev server with proxy to API
```

This can be documented as an alternative for UI developers.

