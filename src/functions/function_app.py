"""NOCLAR Functions app — Python v2 programming model (Blueprint layout).

This file only holds the top-level `FunctionApp` instance and the
`register_blueprint(...)` calls that wire per-lab handler files into it.

The handler files themselves live next to this one:

  * log_request.py        — Lab 04 (governance audit log)
  * persist_assessment.py — Lab 02 (write approved memo)
  * notify_reviewer.py    — Lab 02 (enqueue reviewer notification)
  * process_reviewer.py   — Lab 02 (queue trigger sink)

Each blueprint file ships **fully commented**. Labs unblock them by
uncommenting the file and the matching `app.register_blueprint(...)` line
below, then running `azd deploy functions`.
"""

from __future__ import annotations

import logging

import azure.functions as func

logging.basicConfig(level=logging.INFO)

# This object is required even when zero handlers are active — the Functions
# runtime discovers handlers via this app instance plus any blueprints
# registered onto it below.
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ---- Blueprint registrations (ship commented; labs uncomment) -------------
#
# Lab 02 — multi-agent orchestration + HITL:
# from . import persist_assessment as _persist_assessment
# from . import notify_reviewer as _notify_reviewer
# from . import process_reviewer as _process_reviewer
# app.register_blueprint(_persist_assessment.bp)
# app.register_blueprint(_notify_reviewer.bp)
# app.register_blueprint(_process_reviewer.bp)
#
# Lab 04 — Functions as agent tools:
# from . import log_request as _log_request
# app.register_blueprint(_log_request.bp)
