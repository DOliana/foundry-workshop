# """Lab 02 — `notify_reviewer` handler.

# Enqueues a reviewer notification on the `reviewer-inbox` queue. The
# orchestrator calls this after drafting the memo and before persistence — it
# is the *request* half of the HITL handshake. `process_reviewer` is the
# downstream sink that picks the message up.

# Endpoint: POST https://<func-host>/api/notify_reviewer
# Writes:   <storage>/queues/reviewer-inbox

# Ships **fully commented**. Lab 02 step 1 uncomments this file plus the
# matching `app.register_blueprint(...)` line in `function_app.py`, then
# `azd deploy functions` pushes the handler.
# """

# from __future__ import annotations

# import json
# import logging
# import os
# from datetime import datetime

# import azure.functions as func

# from _clients import queue_client

# log = logging.getLogger("noclar-functions.notify_reviewer")

# bp = func.Blueprint()


# @bp.route(route="notify_reviewer", methods=["POST"])
# def notify_reviewer(req: func.HttpRequest) -> func.HttpResponse:
#     """Enqueue a reviewer notification.

#     Body: { conversation_id, case_id, memo_blob_path, summary, requested_reviewer? }
#     The reviewer picks this up out-of-band; in the workshop we use
#     `process_reviewer` (queue trigger) as the downstream sink.
#     """
#     try:
#         body = req.get_json()
#     except ValueError:
#         return func.HttpResponse("invalid json", status_code=400)

#     payload = {
#         "conversation_id": body.get("conversation_id"),
#         "case_id": body.get("case_id"),
#         "memo_blob_path": body.get("memo_blob_path"),
#         "drafted_at": body.get("drafted_at") or datetime.utcnow().isoformat() + "Z",
#         "requested_reviewer": body.get("requested_reviewer"),
#         "summary": body.get("summary"),
#     }

#     queue_name = os.environ.get("REVIEWER_QUEUE_NAME", "reviewer-inbox")
#     q = queue_client().get_queue_client(queue_name)
#     q.send_message(json.dumps(payload, ensure_ascii=False))

#     log.info("Notified reviewer: case_id=%s", payload["case_id"])
#     return func.HttpResponse(
#         json.dumps({"queued": True, "queue": queue_name}),
#         status_code=202,
#         mimetype="application/json",
#     )
