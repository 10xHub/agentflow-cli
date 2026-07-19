"""Media / multimodal configuration loaded from environment variables."""

from __future__ import annotations

import logging
from enum import StrEnum
from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


logger = logging.getLogger("agentflow-cli.media")


class MediaStorageType(StrEnum):
    MEMORY = "memory"
    LOCAL = "local"
    CLOUD = "cloud"
    PG = "pg"


class MediaSettings(BaseSettings):
    """Settings loaded from env vars (prefix-free, matches plan)."""

    MEDIA_STORAGE_TYPE: MediaStorageType = MediaStorageType.LOCAL
    MEDIA_STORAGE_PATH: str = "./uploads"
    MEDIA_MAX_SIZE_MB: float = 25.0
    DOCUMENT_HANDLING: str = "extract_text"  # extract_text | pass_raw | skip

    # Comma-separated content-type allowlist for uploads. Empty (the default) means
    # accept any type -- the developer's call. Set e.g.
    # ``MEDIA_ALLOWED_CONTENT_TYPES=image/*,application/pdf`` to restrict. Entries may
    # be exact (``image/png``) or wildcard subtype (``image/*``).
    MEDIA_ALLOWED_CONTENT_TYPES: str = ""

    def allowed_content_types(self) -> list[str]:
        """Parsed, normalized allowlist. Empty list == allow all."""
        return [t.strip().lower() for t in self.MEDIA_ALLOWED_CONTENT_TYPES.split(",") if t.strip()]

    def is_content_type_allowed(self, mime: str) -> bool:
        allow = self.allowed_content_types()
        if not allow:
            return True
        mime = mime.split(";", 1)[0].strip().lower()
        top = mime.split("/", 1)[0]
        return mime in allow or f"{top}/*" in allow

    # Cloud storage (S3/GCS) — only used when MEDIA_STORAGE_TYPE=cloud
    MEDIA_CLOUD_PROVIDER: str = "aws"  # aws | gcp
    MEDIA_CLOUD_BUCKET: str = ""
    MEDIA_CLOUD_REGION: str = "us-east-1"
    MEDIA_CLOUD_PREFIX: str = "agentflow-media"
    MEDIA_CLOUD_ACCESS_KEY_ID: str | None = None
    MEDIA_CLOUD_SECRET_ACCESS_KEY: str | None = None
    MEDIA_CLOUD_SESSION_TOKEN: str | None = None
    MEDIA_CLOUD_PROJECT_ID: str | None = None
    MEDIA_CLOUD_CREDENTIALS_JSON: str | None = None

    MEDIA_SIGNED_URL_TTL_SECONDS: int = 3600
    MEDIA_SIGNED_URL_REFRESH_BUFFER_SECONDS: int = 60

    model_config = ConfigDict(extra="allow")


@lru_cache
def get_media_settings() -> MediaSettings:
    return MediaSettings()  # type: ignore[call-arg]
