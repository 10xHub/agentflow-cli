"""Media / multimodal configuration loaded from environment variables."""

from __future__ import annotations

import logging
from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger("agentflow-cli.media")


class MediaStorageType(str, Enum):
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

    # Cloud storage (S3/GCS) — only used when MEDIA_STORAGE_TYPE=cloud
    MEDIA_CLOUD_PROVIDER: str = "aws"  # aws | gcp
    MEDIA_CLOUD_BUCKET: str = ""
    MEDIA_CLOUD_REGION: str = "us-east-1"

    class Config:
        extra = "allow"


@lru_cache
def get_media_settings() -> MediaSettings:
    return MediaSettings()  # type: ignore[call-arg]
