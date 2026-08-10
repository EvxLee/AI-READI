"""Azure Blob access with a local fetch-once cache.

The EDA-era habit was to stream `measurement.csv` (~108 MB) from Azure on
every notebook run. That is slow and pointless: the dataset is frozen. Here a
blob is downloaded once into `data/cache/` and every later call reads the
local copy.

Typical use::

    from aireadi import azure_io

    obs = azure_io.load_table("observation")
    parts = azure_io.load_table("participants")

Credentials come from the environment (optionally via a local `.env`);
nothing here contains a secret.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .constants import CONTAINER_NAME, PATHS, STUDY_ID

__all__ = [
    "repo_root",
    "cache_dir",
    "get_container",
    "fetch",
    "load_table",
    "load_csv",
    "read_dataset_description",
    "clear_cache",
]


def repo_root() -> Path:
    """Repository root, found by walking up from this file."""
    return Path(__file__).resolve().parents[2]


def cache_dir() -> Path:
    """Local blob cache. Gitignored; safe for participant-level files."""
    d = Path(os.getenv("AIREADI_CACHE_DIR", repo_root() / "data" / "cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_env() -> None:
    load_dotenv(repo_root() / ".env", override=False)


def _connection_string() -> str:
    _load_env()
    cs = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if not cs:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is not set. Copy .env.example to "
            ".env and fill in the connection string."
        )
    return cs


def container_name() -> str:
    _load_env()
    return os.getenv("AZURE_CONTAINER_NAME", CONTAINER_NAME)


def study_id() -> str:
    _load_env()
    return os.getenv("AZURE_STUDY_ID", STUDY_ID)


def get_container():
    """Return an Azure ContainerClient. Requires network + credentials."""
    from azure.storage.blob import BlobServiceClient  # imported lazily

    service = BlobServiceClient.from_connection_string(_connection_string())
    return service.get_container_client(container_name())


def fetch(blob_path: str, *, force: bool = False) -> Path:
    """Download `blob_path` into the local cache and return the local path.

    A cached file is reused unless `force=True`. The cache mirrors the blob
    layout, so paths stay recognisable.
    """
    local = cache_dir() / blob_path
    if local.exists() and not force:
        return local

    local.parent.mkdir(parents=True, exist_ok=True)
    container = get_container()
    tmp = local.with_suffix(local.suffix + ".partial")
    with open(tmp, "wb") as fh:
        container.get_blob_client(blob_path).download_blob().readinto(fh)
    tmp.replace(local)  # atomic, so an interrupted download never looks cached
    return local


def load_csv(blob_path: str, *, sep: str | None = None, force: bool = False,
             **read_csv_kwargs) -> pd.DataFrame:
    """Fetch a delimited blob if needed, then read it into a DataFrame."""
    local = fetch(blob_path, force=force)
    if sep is None:
        sep = "\t" if local.suffix.lower() in {".tsv", ".tab"} else ","
    read_csv_kwargs.setdefault("low_memory", False)
    return pd.read_csv(local, sep=sep, **read_csv_kwargs)


def load_table(name: str, *, force: bool = False, **read_csv_kwargs) -> pd.DataFrame:
    """Load a known dataset table by short name.

    Valid names are the keys of `constants.PATHS`, e.g. "observation",
    "measurement", "participants", "manifest_cgm".
    """
    if name not in PATHS:
        raise KeyError(f"Unknown table {name!r}. Known: {sorted(PATHS)}")
    path = PATHS[name].replace(STUDY_ID, study_id(), 1)
    return load_csv(path, force=force, **read_csv_kwargs)


def read_dataset_description(*, force: bool = False) -> dict:
    """Return the container's `dataset_description.json`.

    Use this to confirm which release an analysis ran against; every paper
    must state its dataset version.
    """
    local = fetch(PATHS["dataset_description"].replace(STUDY_ID, study_id(), 1),
                  force=force)
    with open(local, encoding="utf-8") as fh:
        return json.load(fh)


def clear_cache() -> int:
    """Delete every cached blob. Returns the number of files removed."""
    root = cache_dir()
    removed = 0
    for p in sorted(root.rglob("*"), reverse=True):
        if p.is_file():
            p.unlink()
            removed += 1
        elif p.is_dir():
            p.rmdir()
    return removed
