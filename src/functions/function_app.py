"""NOCLAR Functions app — Python v2 programming model.

The workshop ships this file with **all handlers commented out**. Each lab
uncomments the handler(s) it needs:

  Lab 01 (intake + first tool):
    * log_request        — POST /api/log_request   (governance: log at conversation start)

  Lab 02 (orchestration + HITL):
    * persist_assessment — POST /api/persist_assessment   (HITL output: persist approved memo)
    * notify_reviewer    — POST /api/notify_reviewer      (HITL request: enqueue review)
    * process_reviewer   — Queue trigger on reviewer-inbox (downstream sink for the queue)

    Lab 02 also requires uncommenting `_queue_client()` below.

To enable a handler: remove the leading `# ` from every line of its block (the
block is bounded by `# --- BEGIN handler ---` / `# --- END handler ---`
markers) and run `azd deploy functions`.

All blob/queue access uses Managed Identity — no connection strings.
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

# This object is required even when zero handlers are active — the Functions
# runtime discovers handlers by walking decorators on this app instance.
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ---- Lazy clients (constructed on first call) ----------------------------
#
# Module-level globals so the credential and SDK clients are reused across
# warm invocations within the same worker. DefaultAzureCredential resolves
# to the Function App's system-assigned Managed Identity at runtime.

_credential: DefaultAzureCredential | None = None
_blob: BlobServiceClient | None = None
_queue: QueueServiceClient | None = None


def _blob_client() -> BlobServiceClient:
    """Used by `log_request` (Lab 01) and `persist_assessment` (Lab 02)."""
    global _credential, _blob
    if _blob is None:
        _credential = _credential or DefaultAzureCredential()
        _blob = BlobServiceClient(
            account_url=os.environ["AZURE_STORAGE_BLOB_ENDPOINT"],
            credential=_credential,
        )
    return _blob


# --- BEGIN _queue_client (uncomment in Lab 02) ---
# def _queue_client() -> QueueServiceClient:
#     """Used by `notify_reviewer` (Lab 02). The Lab 02 README walks you through enabling this."""
#     global _credential, _queue
#     if _queue is None:
#         _credential = _credential or DefaultAzureCredential()
#         _queue = QueueServiceClient(
#             account_url=os.environ["AZURE_STORAGE_QUEUE_ENDPOINT"],
#             credential=_credential,
#         )
#     return _queue
# --- END _queue_client ---


# --- BEGIN log_request -----------------------------------------------------
# Governance log written at the start of every conversation (chat or voice).
# Attached to the `noclar-intake` agent as an OpenAPI tool in Lab 01.
# Endpoint: POST https://<func-host>/api/log_request
# Writes one blob to: <storage>/logs/YYYY/MM/DD/<conversation_id>.json
#
# Uncomment the block below in **Lab 01, step 4** before `azd deploy functions`.

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
        "locale": body.get("locale", "en-US"),
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
# --- END log_request ---


# --- BEGIN persist_assessment ----------------------------------------------
# Writes the final, HITL-approved Initial Assessment Memo as JSON to the
# `assessments` container. Refuses to persist unless `approved_by` is set —
# this is persistence-layer enforcement of the HITL gate (defence in depth
# against an agent that decides to skip the reviewer step).
#
# Endpoint: POST https://<func-host>/api/persist_assessment
# Writes to:        <storage>/assessments/<case_id>/memo-<timestamp>.json
#
# Uncomment in **Lab 02** (orchestration + HITL) before re-deploying.
#
# @app.route(route="persist_assessment", methods=["POST"])
# def persist_assessment(req: func.HttpRequest) -> func.HttpResponse:
#     """Persist an approved Initial Assessment Memo to the `assessments` container.
#
#     Expects the full AssessmentMemo JSON in the body. Refuses to persist unless
#     `approved_by` is set (HITL gate enforcement at the persistence layer).
#     """
#     try:
#         memo = req.get_json()
#     except ValueError:
#         return func.HttpResponse("invalid json", status_code=400)
#
#     if not memo.get("approved_by"):
#         return func.HttpResponse(
#             json.dumps({"error": "memo missing approved_by — HITL gate not satisfied"}),
#             status_code=409,
#             mimetype="application/json",
#         )
#
#     case_id = memo.get("case_id") or str(uuid.uuid4())
#     container = os.environ.get("ASSESSMENTS_CONTAINER", "assessments")
#     blob_name = f"{case_id}/memo-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
#     _blob_client().get_blob_client(container=container, blob=blob_name).upload_blob(
#         json.dumps(memo, ensure_ascii=False, indent=2),
#         overwrite=False,
#     )
#
#     log.info("Persisted assessment: case_id=%s blob=%s", case_id, blob_name)
#     return func.HttpResponse(
#         json.dumps({"case_id": case_id, "memo_blob": blob_name}),
#         status_code=201,
#         mimetype="application/json",
#     )
# --- END persist_assessment ---


# --- BEGIN notify_reviewer -------------------------------------------------
# Enqueues a reviewer notification on the `reviewer-inbox` queue. The agent
# calls this after drafting the memo and before persistence — it is the
# *request* half of the HITL handshake. `process_reviewer` below is the
# downstream sink that picks the message up.
#
# Endpoint: POST https://<func-host>/api/notify_reviewer
# Writes to:        <storage>/queues/reviewer-inbox
#
# Uncomment in **Lab 02**. Also uncomment `_queue_client()` above.
#
# @app.route(route="notify_reviewer", methods=["POST"])
# def notify_reviewer(req: func.HttpRequest) -> func.HttpResponse:
#     """Enqueue a reviewer notification.
#
#     Body: { conversation_id, case_id, memo_blob_path, summary, requested_reviewer? }
#     The reviewer picks this up out-of-band; in the workshop we use
#     `process_reviewer` (queue trigger below) as the downstream sink.
#     """
#     try:
#         body = req.get_json()
#     except ValueError:
#         return func.HttpResponse("invalid json", status_code=400)
#
#     payload = {
#         "conversation_id": body.get("conversation_id"),
#         "case_id": body.get("case_id"),
#         "memo_blob_path": body.get("memo_blob_path"),
#         "drafted_at": body.get("drafted_at") or datetime.utcnow().isoformat() + "Z",
#         "requested_reviewer": body.get("requested_reviewer"),
#         "summary": body.get("summary"),
#     }
#
#     queue_name = os.environ.get("REVIEWER_QUEUE_NAME", "reviewer-inbox")
#     queue = _queue_client().get_queue_client(queue_name)
#     queue.send_message(json.dumps(payload, ensure_ascii=False))
#
#     log.info("Notified reviewer: case_id=%s", payload["case_id"])
#     return func.HttpResponse(
#         json.dumps({"queued": True, "queue": queue_name}),
#         status_code=202,
#         mimetype="application/json",
#     )
# --- END notify_reviewer ---


# --- BEGIN process_reviewer ------------------------------------------------
# Queue-triggered handler that drains `reviewer-inbox`. Not exposed via HTTP
# and not called by any agent — it runs automatically whenever a message
# lands on the queue. In production this would post to Teams or email; in
# the workshop we keep it observable via App Insights.
#
# Uncomment in **Lab 02**.
#
# @app.queue_trigger(
#     arg_name="msg",
#     queue_name="%REVIEWER_QUEUE_NAME%",
#     connection="AzureWebJobsStorage",
# )
# def process_reviewer(msg: func.QueueMessage) -> None:
#     """Demo queue trigger — logs the reviewer notification.
#
#     In a real deployment this would send a Teams card or email. For the
#     workshop we keep it observable via App Insights.
#     """
#     try:
#         payload = json.loads(msg.get_body().decode("utf-8"))
#     except Exception:
#         payload = {"raw": msg.get_body().decode("utf-8", errors="replace")}
#     log.info("Reviewer queue received: %s", json.dumps(payload, ensure_ascii=False))
# --- END process_reviewer ---
