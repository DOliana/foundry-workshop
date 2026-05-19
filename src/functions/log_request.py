# """Lab 04 — `log_request` handler (governance audit log).

# Writes one JSON blob per conversation to the `logs` container at the very
# start of every conversation (chat or voice). Attached to the
# `noclar-intake` (and other) agents as an OpenAPI tool in Lab 04.

# Endpoint: POST https://<func-host>/api/log_request
# Writes:   <storage>/logs/YYYY/MM/DD/<conversation_id>.json

# Ships **fully commented**. Lab 04 step 1 uncomments this file plus the
# matching `app.register_blueprint(...)` line in `function_app.py`, then
# `azd deploy functions` pushes the handler.
# """

# from __future__ import annotations

# import json
# import logging
# import os
# import uuid
# from datetime import datetime

# import azure.functions as func

# from _clients import blob_client

# log = logging.getLogger("noclar-functions.log_request")

# bp = func.Blueprint()


# @bp.route(route="log_request", methods=["POST"])
# def log_request(req: func.HttpRequest) -> func.HttpResponse:
#     """Persist a governance log entry to the `logs` container.

#     Called by the agent at the start of every conversation (chat or voice).
#     Returns 201 with the assigned log id. Idempotent on (conversation_id, started_at).
#     """
#     try:
#         body = req.get_json()
#     except ValueError:
#         return func.HttpResponse("invalid json", status_code=400)

#     conversation_id = body.get("conversation_id") or str(uuid.uuid4())
#     entry = {
#         "conversation_id": conversation_id,
#         "user_principal": body.get("user_principal"),
#         "started_at": body.get("started_at") or datetime.utcnow().isoformat() + "Z",
#         "channel": body.get("channel", "chat"),
#         "locale": body.get("locale", "en-US"),
#         "intent": body.get("intent"),
#         "metadata": body.get("metadata", {}),
#     }

#     container = os.environ.get("LOGS_CONTAINER", "logs")
#     blob_name = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{conversation_id}.json"
#     blob_client().get_blob_client(container=container, blob=blob_name).upload_blob(
#         json.dumps(entry, ensure_ascii=False, indent=2),
#         overwrite=True,
#     )

#     log.info("Logged request: conversation_id=%s blob=%s", conversation_id, blob_name)
#     return func.HttpResponse(
#         json.dumps({"conversation_id": conversation_id, "log_blob": blob_name}),
#         status_code=201,
#         mimetype="application/json",
#     )
