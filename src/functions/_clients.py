"""Shared lazy clients for the Functions blueprints.

All blueprint files import `_blob_client()` and `_queue_client()` from this
module so the credential + SDK clients are reused across warm invocations
within the same worker. DefaultAzureCredential resolves to the Function App's
system-assigned Managed Identity at runtime.
"""

from __future__ import annotations

import os

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

_credential: DefaultAzureCredential | None = None
_blob: BlobServiceClient | None = None
_queue: QueueServiceClient | None = None


def _get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def blob_client() -> BlobServiceClient:
    """Used by `log_request` (Lab 04) and `persist_assessment` (Lab 02)."""
    global _blob
    if _blob is None:
        _blob = BlobServiceClient(
            account_url=os.environ["AZURE_STORAGE_BLOB_ENDPOINT"],
            credential=_get_credential(),
        )
    return _blob


def queue_client() -> QueueServiceClient:
    """Used by `notify_reviewer` (Lab 02)."""
    global _queue
    if _queue is None:
        _queue = QueueServiceClient(
            account_url=os.environ["AZURE_STORAGE_QUEUE_ENDPOINT"],
            credential=_get_credential(),
        )
    return _queue
