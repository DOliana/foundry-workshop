"""NOCLAR Orchestrator — multi-agent workflow with two HITL gates (Block 2).

Sketches the workflow that participants build step-by-step in Lab 02.

```
intake -> grounded enrichment -> legal classifier -> HITL #1 confirm
       -> drafter -> HITL #2 approve -> persist_assessment -> notify_reviewer
```

This module intentionally exposes the workflow as small, testable functions
so the lab can inspect each step in App Insights.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential

from src.agents.tools.functions_tools import notify_reviewer, persist_assessment
from src.shared.config import get_settings
from src.shared.schemas import (
    AssessmentMemo,
    IntakeFacts,
    LegalNormReference,
)

PROMPTS = Path(__file__).parent / "prompts"


def _approve_via_console(prompt: str, payload: object) -> bool:
    """Default HITL impl — print payload, read y/n from stdin.

    Labs replace this with a Teams card / web UI; the function signature is
    what matters for the workflow.
    """
    print("\n=== HITL CHECKPOINT ===")
    print(prompt)
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return input("Approve (y/N)? ").strip().lower() == "y"


def run_workflow(
    intake: IntakeFacts,
    *,
    user_principal: str,
    approve_classification: Callable[[str, object], bool] = _approve_via_console,
    approve_memo: Callable[[str, object], bool] = _approve_via_console,
) -> dict[str, str]:
    """Run the full orchestration. Returns paths of persisted artifacts."""

    settings = get_settings()
    client = AgentsClient(
        endpoint=settings.foundry_project_endpoint,
        credential=DefaultAzureCredential(),
    )

    conversation_id = str(uuid.uuid4())

    # 1. Enrich with grounded agent
    grounded_findings = _ask_specialist(
        client,
        agent_name="noclar-grounded",
        message=f"Which internal policies and external norms are relevant to this matter?\n\n{intake.summary}",
    )

    # 2. Legal classification (proposal)
    classifier_input = {
        "intake": intake.model_dump(),
        "grounded_findings": grounded_findings,
    }
    classification_raw = _ask_specialist(
        client,
        agent_name="noclar-legal-classifier",
        message=json.dumps(classifier_input, ensure_ascii=False),
    )
    proposed = [LegalNormReference(**n) for n in json.loads(classification_raw)]

    # 3. HITL #1 — confirm classification
    if not approve_classification(
        "Please confirm the legal classification (HITL #1):",
        [n.model_dump() for n in proposed],
    ):
        raise RuntimeError("Classification rejected — workflow stopped.")

    # 4. Drafter
    drafter_input = {
        "intake": intake.model_dump(),
        "grounded_findings": grounded_findings,
        "legal_assessment": [n.model_dump() for n in proposed],
    }
    draft_raw = _ask_specialist(
        client,
        agent_name="noclar-drafter",
        message=json.dumps(drafter_input, ensure_ascii=False),
    )
    memo = AssessmentMemo(**json.loads(draft_raw))

    # 5. HITL #2 — approve memo
    if not approve_memo(
        "Approve the Initial Assessment Memo (HITL #2):",
        memo.model_dump(),
    ):
        raise RuntimeError("Memo rejected — workflow stopped.")

    memo.approved_by = user_principal
    memo.approved_at = datetime.utcnow()

    # 6. Persist + notify
    persist_result = persist_assessment(memo.model_dump(mode="json"))
    notify_reviewer(
        conversation_id=conversation_id,
        case_id=memo.case_id,
        memo_blob_path=persist_result["memo_blob"],
        summary=memo.intake.summary,
        requested_reviewer="audit_committee@helios-industrieanlagen.example",
    )

    return {
        "conversation_id": conversation_id,
        "memo_blob": persist_result["memo_blob"],
    }


def _ask_specialist(client: AgentsClient, agent_name: str, message: str) -> str:
    """Helper: send a single message to a specialist agent and return text."""
    agents = list(client.list_agents())
    agent = next((a for a in agents if a.name == agent_name), None)
    if agent is None:
        raise RuntimeError(
            f"Specialist '{agent_name}' not provisioned. "
            "Run `python scripts/seed_foundry_project.py` first."
        )
    thread = client.threads.create()
    client.messages.create(thread_id=thread.id, role="user", content=message)
    run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    if run.status != "completed":
        raise RuntimeError(f"Specialist '{agent_name}' failed: {run.last_error}")
    for msg in client.messages.list(thread_id=thread.id):
        if msg.role == "assistant":
            for content in msg.content:
                if content.type == "text":
                    return content.text.value
    raise RuntimeError(f"Specialist '{agent_name}' returned no text content.")
