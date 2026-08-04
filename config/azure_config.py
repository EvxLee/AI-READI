"""
Azure Blob Storage configuration.

This module intentionally contains **no secrets**.
Connection details are loaded from environment variables (optionally via a local
`.env` file) so that credentials never need to be committed to version control.

Required environment variables:
    AZURE_STORAGE_CONNECTION_STRING  - Full Azure Blob Storage connection string.
    AZURE_CONTAINER_NAME             - Target container name (e.g. "aireadi-raw").

Optional:
    AZURE_STUDY_ID                   - Study identifier used by some scripts/notebooks.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "See .env.example and README for setup instructions."
        )
    return value


CONNECTION_STRING: str = _require_env("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME: str = os.getenv("AZURE_CONTAINER_NAME", "aireadi-raw")
STUDY_ID: str = os.getenv("AZURE_STUDY_ID", "00b62456-0b93-4975-a992-42ba6a50ed5c")

