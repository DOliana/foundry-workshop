"""NOCLAR Functions app — Python v2 programming model.

Functions deployed:
  * log_request        — POST /api/log_request          (governance: log at conversation start)
  * persist_assessment — POST /api/persist_assessment   (HITL output: persist approved memo)
  * notify_reviewer    — POST /api/notify_reviewer      (HITL request: route to reviewer queue)
  * process_reviewer   — Queue trigger on reviewer-inbox (placeholder for downstream routing)

All blob/queue access uses Managed Identity (no connection strings).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("noclar-functions")

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ---- Lazy clients (constructed on first call) ----

_credential: DefaultAzureCredential | None = None
_blob: BlobServiceClient | None = None
_queue: QueueServiceClient | None = None


def _blob_client() -> BlobServiceClient:
    global _credential, _blob
    if _blob is None:
        _credential = _credential or DefaultAzureCredential()
        _blob = BlobServiceClient(
            account_url=os.environ["AZURE_STORAGE_BLOB_ENDPOINT"],
            credential=_credential,
        )
    return _blob


def _queue_client() -> QueueServiceClient:
    global _credential, _queue
    if _queue is None:
        _credential = _credential or DefaultAzureCredential()
        _queue = QueueServiceClient(
            account_url=os.environ["AZURE_STORAGE_QUEUE_ENDPOINT"],
            credential=_credential,
        )
    return _queue


# ---- log_request: governance log at conversation start ----

@app.route(route="log_request", methods=["POST"])
def log_request(req: func.HttpRequest) -> func.HttpResponse:
    """Persist a governance log entry to the `logs` container.

    Called by the agent at the start of every conversation (chat or voice).
    Returns 201 with the assigned log id. Idempotent on (conversation_id, started_at).
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid json", status_code=400)

    conversation_id = body.get("conversation_id") or str(uuid.uuid4())
    entry = {
        "conversation_id": conversation_id,
        "user_principal": body.get("user_principal"),
        "started_at": body.get("started_at") or datetime.utcnow().isoformat() + "Z",
        "channel": body.get("channel", "chat"),
        "locale": body.get("locale", "de-DE"),
        "intent": body.get("intent"),
        "metadata": body.get("metadata", {}),
    }

    container = os.environ.get("LOGS_CONTAINER", "logs")
    blob_name = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{conversation_id}.json"
    _blob_client().get_blob_client(container=container, blob=blob_name).upload_blob(
        json.dumps(entry, ensure_ascii=False, indent=2),
        overwrite=True,
    )

    log.info("Logged request: conversation_id=%s blob=%s", conversation_id, blob_name)
    return func.HttpResponse(
        json.dumps({"conversation_id": conversation_id, "log_blob": blob_name}),
        status_code=201,
        mimetype="application/json",
    )


# ---- persist_assessment: write approved memo ----

@app.route(route="persist_assessment", methods=["POST"])
def persist_assessment(req: func.HttpRequest) -> func.HttpResponse:
    """Persist an approved Initial Assessment Memo to the `assessments` container.

    Expects the full AssessmentMemo JSON in the body. Refuses to persist unless
    `approved_by` is set (HITL gate enforcement at the persistence layer).
    """
    try:
        memo = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid json", status_code=400)

    if not memo.get("approved_by"):
        return func.HttpResponse(
            json.dumps({"error": "memo missing approved_by — HITL gate not satisfied"}),
            status_code=409,
            mimetype="application/json",
        )

    case_id = memo.get("case_id") or str(uuid.uuid4())
    container = os.environ.get("ASSESSMENTS_CONTAINER", "assessments")
    blob_name = f"{case_id}/memo-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    _blob_client().get_blob_client(container=container, blob=blob_name).upload_blob(
        json.dumps(memo, ensure_ascii=False, indent=2),
        overwrite=False,
    )

    log.info("Persisted assessment: case_id=%s blob=%s", case_id, blob_name)
    return func.HttpResponse(
        json.dumps({"case_id": case_id, "memo_blob": blob_name}),
        status_code=201,
        mimetype="application/json",
    )


# ---- notify_reviewer: route HITL approval request to queue ----

@app.route(route="notify_reviewer", methods=["POST"])
def notify_reviewer(req: func.HttpRequest) -> func.HttpResponse:
    """Enqueue a reviewer notification.

    Body: { conversation_id, case_id, memo_blob_path, summary, requested_reviewer? }
    The reviewer picks this up out-of-band; in the workshop we use
    `process_reviewer` (queue trigger below) as the downstream sink.
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid json", status_code=400)

    payload = {
        "conversation_id": body.get("conversation_id"),
        "case_id": body.get("case_id"),
        "memo_blob_path": body.get("memo_blob_path"),
        "drafted_at": body.get("drafted_at") or datetime.utcnow().isoformat() + "Z",
        "requested_reviewer": body.get("requested_reviewer"),
        "summary": body.get("summary"),
    }

    queue_name = os.environ.get("REVIEWER_QUEUE_NAME", "reviewer-inbox")
    queue = _queue_client().get_queue_client(queue_name)
    # Queue Storage requires base64-encoded text via SDK helper or option
    queue.send_message(json.dumps(payload, ensure_ascii=False))

    log.info("Notified reviewer: case_id=%s", payload["case_id"])
    return func.HttpResponse(
        json.dumps({"queued": True, "queue": queue_name}),
        status_code=202,
        mimetype="application/json",
    )


# ---- process_reviewer: queue trigger demo ----

@app.queue_trigger(
    arg_name="msg",
    queue_name="%REVIEWER_QUEUE_NAME%",
    connection="AzureWebJobsStorage",
)
def process_reviewer(msg: func.QueueMessage) -> None:
    """Demo queue trigger — logs the reviewer notification.

    In a real deployment this would send a Teams card or email. For the
    workshop we keep it observable via App Insights.
    """
    try:
        payload = json.loads(msg.get_body().decode("utf-8"))
    except Exception:
        payload = {"raw": msg.get_body().decode("utf-8", errors="replace")}
    log.info("Reviewer queue received: %s", json.dumps(payload, ensure_ascii=False))
