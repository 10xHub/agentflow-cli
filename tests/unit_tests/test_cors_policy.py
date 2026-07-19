"""CORS must fail closed in production (audit B6).

`ORIGINS="*"` on its own is a legitimate choice for a public, token-less API, and
a permissive default is normal in development. The dangerous combination is
wildcard origins *with credentials*: Starlette reflects the caller's Origin back
alongside `Access-Control-Allow-Credentials: true`, which makes every origin a
trusted, credentialed one. Previously production merely warned and served it.
"""

from types import SimpleNamespace

import pytest

from agentflow_cli.src.app.core.config.setup_middleware import (
    InsecureCorsConfigError,
    _resolve_cors_policy,
)


def _settings(mode: str, origins: str, credentials: bool = True):
    return SimpleNamespace(MODE=mode, ORIGINS=origins, CORS_ALLOW_CREDENTIALS=credentials)


class TestCorsFailsClosedInProduction:
    def test_production_refuses_wildcard_with_credentials(self):
        with pytest.raises(InsecureCorsConfigError):
            _resolve_cors_policy(_settings("production", "*", credentials=True))

    def test_production_allows_wildcard_without_credentials(self):
        # A public, non-credentialed API is a valid choice.
        origins, creds = _resolve_cors_policy(_settings("production", "*", credentials=False))
        assert origins == ["*"]
        assert creds is False

    def test_production_allows_explicit_origins_with_credentials(self):
        origins, creds = _resolve_cors_policy(
            _settings("production", "https://a.com,https://b.com", credentials=True)
        )
        assert origins == ["https://a.com", "https://b.com"]
        assert creds is True

    def test_development_still_permissive(self):
        # The convenient default must keep working locally.
        origins, creds = _resolve_cors_policy(_settings("development", "*", credentials=True))
        assert origins == ["*"]
        assert creds is True

    def test_origins_are_trimmed(self):
        origins, _ = _resolve_cors_policy(
            _settings("production", " https://a.com , https://b.com ", credentials=True)
        )
        assert origins == ["https://a.com", "https://b.com"]
