"""HTTP tool wrappers around the Functions endpoints.

These are designed to be registered as **function tools** on a Foundry agent:

```python
from agents.tools.functions_tools import log_request, persist_assessment, notify_reviewer
agent.tools = [log_request, persist_assessment, notify_reviewer]
```

In real workshop code, the Foundry Agent Service knows how to turn typed
Python callables into tool definitions; the docstrings here are what the model
sees.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_FUNCTIONS_BASE_URL_ENV = "AZURE_FUNCTION_APP_HOSTNAME"


def _base_url() -> str:
    host = os.environ.get(_FUNCTIONS_BASE_URL_ENV)
    if not host:
        raise RuntimeError(f"{_FUNCTIONS_BASE_URL_ENV} not set")
    if not host.startswith("http"):
        host = f"https://{host}"
    return host.rstrip("/")


def _function_key() -> str | None:
    # Workshop convention: pass the master function key in this env var.
    # In production prefer Entra ID auth via APIM in front of Functions.
    return os.environ.get("AZURE_FUNCTION_KEY")


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    params = {}
    key = _function_key()
    if key:
        params["code"] = key
    r = httpx.post(url, json=body, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def log_request(
    conversation_id: str,
    channel: str = "chat",
    locale: str = "en-US",
    user_principal: str | None = None,
    intent: str | None = None,
) -> dict[str, Any]:
    """Write a governance log entry at the start of a conversation.

    MUST be called at the start of every conversation, before any other
    tools are used or any substantive question is discussed with the user.
    """
    return _post(
        "/api/log_request",
        {
            "conversation_id": conversation_id,
            "channel": channel,
            "locale": locale,
            "user_principal": user_principal,
            "intent": intent,
        },
    )


def persist_assessment(memo: dict[str, Any]) -> dict[str, Any]:
    """Persist an approved Initial Assessment Memo to durable storage.

    The memo MUST already have `approved_by` and `approved_at` set
    (HITL gate). The Function rejects memos that have not been approved.
    """
    return _post("/api/persist_assessment", memo)


def notify_reviewer(
    conversation_id: str,
    case_id: str,
    memo_blob_path: str,
    summary: str,
    requested_reviewer: str | None = None,
) -> dict[str, Any]:
    """Enqueue an approval request in the reviewer queue (HITL #2)."""
    return _post(
        "/api/notify_reviewer",
        {
            "conversation_id": conversation_id,
            "case_id": case_id,
            "memo_blob_path": memo_blob_path,
            "summary": summary,
            "requested_reviewer": requested_reviewer,
        },
    )
