"""Loopback-only HTTP server behind ``agentflow config``.

Routes:
    GET  /               the editor page
    GET  /app.js         the page's bundled script (built from config-editor-ui/)
    GET  /app.css        the page's compiled Tailwind stylesheet
    GET  /api/state      current file, schema, and validation issues
    POST /api/validate   validate a config without saving it
    POST /api/save       validate, then write the config file

Every ``/api`` call must carry the per-run token (sent by the page from the URL
fragment) and a loopback ``Host`` header. That keeps other sites open in the same
browser from reading or overwriting the file, including via DNS rebinding.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any

from agentflow_cli.cli.config_editor.schema import build_schema
from agentflow_cli.cli.config_editor.store import ConfigConflictError, ConfigFileStore
from agentflow_cli.cli.config_editor.validation import has_errors, validate_config


LOOPBACK_HOST = "127.0.0.1"
TOKEN_HEADER = "X-Agentflow-Token"  # noqa: S105 - a header name, not a secret  # nosec B105
MAX_BODY_BYTES = 1_000_000
NEW_FILE_TEMPLATE: dict[str, Any] = {"agent": "graph.agent:app", "env": ".env"}

# Static files the page loads: route -> (file under static/, content type).
_STATIC_FILES: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
}

_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class ConfigEditorServer:
    """Serve the editor for one config file on an ephemeral loopback port."""

    def __init__(self, config_path: Path, port: int = 0, token: str | None = None) -> None:
        self.store = ConfigFileStore(config_path)
        self.token = token or secrets.token_urlsafe(24)
        self._httpd = ThreadingHTTPServer((LOOPBACK_HOST, port), _Handler)
        self._httpd.daemon_threads = True
        self._httpd.editor = self  # type: ignore[attr-defined]
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return int(self._httpd.server_address[1])

    @property
    def url(self) -> str:
        return f"http://{LOOPBACK_HOST}:{self.port}/#token={self.token}"

    def serve_forever(self) -> None:
        self._httpd.serve_forever()

    def start_in_background(self) -> None:
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="agentflow-config-editor", daemon=True
        )
        self._thread.start()

    def shutdown(self) -> None:
        if self._thread is not None:
            self._httpd.shutdown()
            self._thread.join(timeout=5)
            self._thread = None
        self._httpd.server_close()

    # -- request handling ---------------------------------------------------

    def state(self) -> dict[str, Any]:
        loaded = self.store.load()
        config = loaded.config
        issues = validate_config(config, self.store.path.parent) if config is not None else []
        return {
            "path": str(self.store.path),
            "exists": loaded.version is not None,
            "version": loaded.version,
            "parse_error": loaded.parse_error,
            "config": config if config is not None else dict(NEW_FILE_TEMPLATE),
            "schema": build_schema(),
            "issues": issues,
        }

    def validate(self, config: Any) -> dict[str, Any]:
        return {"issues": validate_config(config, self.store.path.parent)}

    def save(self, config: Any, version: str | None) -> tuple[HTTPStatus, dict[str, Any]]:
        issues = validate_config(config, self.store.path.parent)
        if has_errors(issues):
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "error": "Fix the errors before saving.",
                "issues": issues,
            }
        try:
            new_version = self.store.save(config, version)
        except ConfigConflictError as exc:
            return HTTPStatus.CONFLICT, {"error": str(exc), "issues": issues}
        except OSError as exc:
            return HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": f"Could not write {self.store.path}: {exc}",
                "issues": issues,
            }
        backup = self.store.backup_path
        return HTTPStatus.OK, {
            "version": new_version,
            "config": self.store.load().config,  # as written, in the file's key order
            "path": str(self.store.path),
            "backup": str(backup) if backup.exists() else None,
            "issues": issues,
        }

    def allowed_hosts(self) -> set[str]:
        return {f"{LOOPBACK_HOST}:{self.port}", f"localhost:{self.port}"}


class _Handler(BaseHTTPRequestHandler):
    server_version = "AgentflowConfig"

    @property
    def editor(self) -> ConfigEditorServer:
        return self.server.editor  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Keep the terminal quiet; the CLI prints its own status."""

    def do_GET(self) -> None:
        if not self._host_allowed():
            return
        route = self.path.split("?", 1)[0]
        if route in _STATIC_FILES:
            name, content_type = _STATIC_FILES[route]
            asset = files("agentflow_cli.cli.config_editor").joinpath("static", name)
            self._send(HTTPStatus.OK, asset.read_bytes(), content_type)
        elif route == "/api/state":
            if self._authorized():
                self._send_json(HTTPStatus.OK, self.editor.state())
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self._host_allowed() or not self._authorized():
            return
        body = self._read_json()
        if body is None:
            return
        route = self.path.split("?", 1)[0]
        if route == "/api/validate":
            self._send_json(HTTPStatus.OK, self.editor.validate(body.get("config")))
        elif route == "/api/save":
            status, payload = self.editor.save(body.get("config"), body.get("version"))
            self._send_json(status, payload)
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    # -- guards ---------------------------------------------------------------

    def _host_allowed(self) -> bool:
        if self.headers.get("Host", "") in self.editor.allowed_hosts():
            return True
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "Unexpected Host header"})
        return False

    def _authorized(self) -> bool:
        supplied = self.headers.get(TOKEN_HEADER, "")
        if hmac.compare_digest(supplied.encode(), self.editor.token.encode()):
            return True
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "Missing or invalid session token"})
        return False

    def _read_json(self) -> dict[str, Any] | None:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/json":
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Expected JSON"})
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Body too large"})
            return None
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON: {exc}"})
            return None
        if not isinstance(body, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Expected a JSON object"})
            return None
        return body

    # -- responses ------------------------------------------------------------

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", _CSP)
        self.end_headers()
        self.wfile.write(body)
