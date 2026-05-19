"""Centralised env-var loading.

Reads values populated by `azd up` (see infra/main.bicep outputs). Also
works for local dev by reading `.env` if present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def load_env() -> None:
    """Best-effort load of `.env` into `os.environ`.

    Lab 00 writes `.env` via `azd env get-values > .env` but never sources
    it. Every lab entrypoint calls this (directly or transitively via
    `src/labs/__init__.py`) so the file is picked up automatically. Safe
    to call repeatedly; `load_dotenv()` is idempotent and a no-op when no
    `.env` is present.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except ImportError:
        pass


# Backwards-compatible alias.
_maybe_load_dotenv = load_env


@dataclass(frozen=True)
class Settings:
    foundry_project_endpoint: str
    foundry_model_deployment: str
    search_endpoint: str
    storage_account: str
    storage_blob_endpoint: str
    storage_queue_endpoint: str
    assessments_container: str
    logs_container: str
    sample_docs_container: str
    reviewer_queue_name: str
    appinsights_connection_string: str | None
    foundry_embedding_deployment: str | None
    foundry_realtime_deployment: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_env()

    def _required(name: str) -> str:
        v = os.environ.get(name)
        if not v:
            raise RuntimeError(
                f"Required env var '{name}' is not set. Run `azd env get-values > .env` first."
            )
        return v

    return Settings(
        foundry_project_endpoint=_required("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"),
        foundry_model_deployment=_required("AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT"),
        search_endpoint=_required("AZURE_AI_SEARCH_ENDPOINT"),
        storage_account=_required("AZURE_STORAGE_ACCOUNT"),
        storage_blob_endpoint=_required("AZURE_STORAGE_BLOB_ENDPOINT"),
        storage_queue_endpoint=_required("AZURE_STORAGE_QUEUE_ENDPOINT"),
        assessments_container=os.environ.get("ASSESSMENTS_CONTAINER", "assessments"),
        logs_container=os.environ.get("LOGS_CONTAINER", "logs"),
        sample_docs_container=os.environ.get("SAMPLE_DOCS_CONTAINER", "sample-docs"),
        reviewer_queue_name=os.environ.get("REVIEWER_QUEUE_NAME", "reviewer-inbox"),
        appinsights_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        foundry_embedding_deployment=os.environ.get("AZURE_AI_FOUNDRY_EMBEDDING_DEPLOYMENT"),
        foundry_realtime_deployment=os.environ.get("AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT"),
    )
