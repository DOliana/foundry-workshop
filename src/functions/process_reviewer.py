"""Lab 02 — `process_reviewer` (queue trigger).

Queue-triggered handler that drains `reviewer-inbox`. Not exposed via HTTP
and not called by any agent — it runs automatically whenever a message
lands on the queue. In production this would post to Teams or email; in
the workshop we keep it observable via App Insights.

Ships **fully commented**. Optional uncomment in Lab 02 step 1.
"""

# from __future__ import annotations
#
# import json
# import logging
#
# import azure.functions as func
#
# log = logging.getLogger("noclar-functions.process_reviewer")
#
# bp = func.Blueprint()
#
#
# @bp.queue_trigger(
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
