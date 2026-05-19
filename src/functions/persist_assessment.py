"""Lab 02 — `persist_assessment` handler.

Writes the final, HITL-approved Initial Assessment Memo as JSON to the
`assessments` container. Refuses to persist (HTTP 409) unless `approved_by`
is set — persistence-layer enforcement of the HITL gate (defence in depth
against an orchestrator that decides to skip the reviewer step).

Endpoint: POST https://<func-host>/api/persist_assessment
Writes:   <storage>/assessments/<case_id>/memo-<timestamp>.json

Ships **fully commented**. Lab 02 step 1 uncomments this file plus the
matching `app.register_blueprint(...)` line in `function_app.py`, then
`azd deploy functions` pushes the handler.
"""

# from __future__ import annotations
#
# import json
# import logging
# import os
# import uuid
# from datetime import datetime
#
# import azure.functions as func
#
# from ._clients import blob_client
#
# log = logging.getLogger("noclar-functions.persist_assessment")
#
# bp = func.Blueprint()
#
#
# @bp.route(route="persist_assessment", methods=["POST"])
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
#     blob_client().get_blob_client(container=container, blob=blob_name).upload_blob(
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
