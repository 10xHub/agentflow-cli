"""Files must be owner-scoped (audit B3 residual).

`MediaService.get_file(file_id)` had no owner concept at all: any *authenticated*
user who knew (or guessed) a file_id got the bytes back. Authentication was being
mistaken for authorization.

Ownership is recorded in the file's own metadata at upload, so it is exactly as
durable as the file -- a cache entry would expire and silently un-own it.
"""

from types import SimpleNamespace

import pytest

from agentflow_cli.src.app.routers.media import MediaService


def _service(metadata: dict, require_owner: bool = False) -> MediaService:
    svc = MediaService.__new__(MediaService)
    svc._settings = SimpleNamespace(MEDIA_REQUIRE_OWNER=require_owner)

    async def get_metadata(file_id):
        return metadata.get(file_id)

    svc._store = SimpleNamespace(get_metadata=get_metadata)
    return svc


FILES = {
    "alice-file": {"filename": "secret.pdf", "owner_id": "alice"},
    "legacy-file": {"filename": "old.pdf"},  # uploaded before ownership existed
}


class TestFileOwnership:
    @pytest.mark.asyncio
    async def test_owner_can_access_own_file(self):
        await _service(FILES).ensure_can_access("alice-file", "alice")

    @pytest.mark.asyncio
    async def test_other_user_cannot_access(self):
        """The hole: knowing the id was enough."""
        with pytest.raises(PermissionError):
            await _service(FILES).ensure_can_access("alice-file", "mallory")

    @pytest.mark.asyncio
    async def test_missing_file_raises_key_error(self):
        with pytest.raises(KeyError):
            await _service(FILES).ensure_can_access("nope", "alice")

    @pytest.mark.asyncio
    async def test_unauthenticated_check_is_skipped(self):
        # No user identity (auth not configured) -> nothing to scope by.
        await _service(FILES).ensure_can_access("alice-file", None)

    @pytest.mark.asyncio
    async def test_legacy_file_without_owner_is_allowed_by_default(self):
        # Files predating ownership must not become unreadable on upgrade.
        await _service(FILES).ensure_can_access("legacy-file", "alice")

    @pytest.mark.asyncio
    async def test_legacy_file_denied_when_owner_required(self):
        # Deployments that need a hard guarantee can opt in.
        with pytest.raises(PermissionError):
            await _service(FILES, require_owner=True).ensure_can_access("legacy-file", "alice")

    def test_method_name_is_mock_safe(self):
        # A name starting with "assert" collides with unittest.mock's assertion
        # namespace, so AsyncMock refuses to auto-create it and every consumer
        # mocking MediaService breaks. Keep it out of that namespace.
        assert not MediaService.ensure_can_access.__name__.startswith("assert")
