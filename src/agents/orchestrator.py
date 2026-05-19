"""NOCLAR Orchestrator — local Python + Microsoft Agent Framework.

This is the **primary** orchestrator for Lab 02. It runs on your laptop,
talks to the three hosted Foundry agents (`noclar-intake`,
`noclar-legal-classifier`, `noclar-drafter`) as sub-agents via Microsoft
Agent Framework, and enforces two HITL checkpoints with stdin prompts.

Flow:

    intake (interactive, multi-turn)
        -> legal_classifier (single shot, JSON)
        -> HITL #1 in terminal
        -> drafter (single shot, JSON)
        -> HITL #2 in terminal
        -> persist_assessment Function (server-side HITL gate: 409 if
           approved_by missing)
        -> notify_reviewer Function

Why a local script, not a hosted orchestrator agent?

    - Deterministic Python control flow is easier to reason about (and
      easier to test) than an LLM-based orchestrator you have to
      prompt-engineer into following the right order.
    - HITL gates are plain ``input()`` calls, not chat messages.
    - The three specialist agents are still hosted Foundry agents — the
      prompt team can iterate on them in the portal without touching
      this script.
    - This is the "production pattern" for NOCLAR. In a real EY product
      the stdin prompts become Teams adaptive cards / web modals and
      this script becomes a Durable Function, but the shape is the same.

Run:

    python -m src.agents.orchestrator                # full workflow
    python -m src.agents.orchestrator --bypass-hitl  # negative-path demo
                                                     # (Function returns 409)

Required env vars (export them, or put them in a ``.env``):

    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT
        e.g. https://foundry-xxx.services.ai.azure.com/api/projects/noclar-assessment
    AZURE_FUNCTION_APP_HOSTNAME
        e.g. func-noclar-xxx.azurewebsites.net
    AZURE_FUNCTION_KEY
        master key from ``az functionapp keys list``
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import uuid
from datetime import datetime

from agent_framework.foundry import FoundryAgent
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

from src.agents.tools.functions_tools import notify_reviewer, persist_assessment
from src.shared.schemas import AssessmentMemo, IntakeFacts, LegalNormReference

INTAKE_AGENT = "noclar-intake"
CLASSIFIER_AGENT = "noclar-legal-classifier"
DRAFTER_AGENT = "noclar-drafter"

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

def _hdr(label: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {label}")
    print("=" * 72)


def _extract_json(text: str) -> str:
    """Tolerate the occasional ```json ... ``` fence that creeps through
    even with *Response format = JSON object* configured on the agent."""
    m = _JSON_FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _approve_in_terminal(label: str, payload: object) -> tuple[bool, str]:
    """HITL gate — print the payload, prompt for `approve` / anything else."""
    _hdr(f"HITL CHECKPOINT — {label}")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    print()
    answer = input(
        "Approve? Type 'approve' to continue, anything else to reject: "
    ).strip().lower()
    if answer == "approve":
        comments = input("Optional comments (press Enter to skip): ").strip()
        print("  -> APPROVED")
        return True, comments
    reason = input("Reason for rejection: ").strip()
    print("  -> REJECTED")
    return False, reason


# ---------------------------------------------------------------------------
# Specialist invocation
# ---------------------------------------------------------------------------

async def _interactive_intake(intake_agent) -> dict:
    """Drive a multi-turn intake conversation in the terminal.

    Uses Agent Framework sessions for server-side conversational state.
    For multiline pastes, type `/paste` and finish with `/end` so the
    whole block is sent as a single user turn.
    """
    _hdr("Step 1 — Intake conversation")
    print("Type your messages. Type 'done' when intake is complete.")
    print("For multiline text, type '/paste' then end with '/end'.")
    print("For the workshop demo, open these two files in your editor and")
    print("paste their contents (or summarise them) when the agent asks for")
    print("documents — the hosted agent has no filesystem access:")
    print("  data/sample-docs/intake-email-01-anonymous-tip.md")
    print("  data/sample-docs/intake-email-02-internal-whistleblower.md\n")

    session = intake_agent.create_session()
    # Prime the conversation — the agent will call its `log_request` tool
    # here as the intake prompt requires (governance hook from Lab 01).
    print(f"  [Agent: {INTAKE_AGENT}] Starting session (demo mode — condensed intake)...")
    print("  The agent will ask all fields at once. Answer in one block, then type 'done'.")
    print("  To paste a document, type '/paste' and end with '/end'.\n")
    primer = await intake_agent.run(
        "Begin the NOCLAR intake in WORKSHOP / DEMO mode. "
        "Greet the user in one sentence, then ask ALL required fields in a "
        "single bundled message (client name, trigger, key facts, persons "
        "involved, suspected norm, urgency). "
        "Skip individual read-backs and confirmations — accept the first "
        "answer the user gives and move on immediately. "
        "The goal is to reach a complete IntakeFacts JSON in 2–3 turns total.",
        session=session,
    )
    print(f"[{INTAKE_AGENT}]> {primer.text}\n")

    while True:
        try:
            user_msg = input("You> ").strip()
        except EOFError:
            print("\n[STOP] Input stream closed. Aborting instead of auto-submitting.")
            raise SystemExit(1)

        if not user_msg:
            continue

        lowered = user_msg.lower()
        if lowered in ("/paste", "paste"):
            print("Paste mode enabled. End with '/end' on its own line.")
            lines: list[str] = []
            while True:
                try:
                    line = input("... ")
                except EOFError:
                    print("\n[STOP] Input stream closed during paste mode.")
                    raise SystemExit(1)
                if line.strip().lower() in ("/end", "end"):
                    break
                lines.append(line)
            user_msg = "\n".join(lines).strip()
            if not user_msg:
                continue
            lowered = user_msg.lower()

        if lowered in ("done", "quit", "exit"):
            print(f"\n  [Agent: {INTAKE_AGENT}] Finalising intake — producing IntakeFacts JSON...")
            final = await intake_agent.run(
                "The user has signalled intake is complete. Produce the "
                "final IntakeFacts JSON object and nothing else.",
                session=session,
            )
            print(f"\n[{INTAKE_AGENT}]> {final.text}\n")
            text = _extract_json(final.text)
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                print(
                    f"\n[ERROR] Agent did not return valid JSON: {exc}\n"
                    "  The agent may still need more information. Continue the "
                    "conversation or type 'done' again once the agent confirms "
                    "all fields are collected.\n"
                )
                continue

        reply = await intake_agent.run(user_msg, session=session)
        print(f"\n[{INTAKE_AGENT}]> {reply.text}\n")


async def _call_specialist_json(agent, payload: dict, agent_name: str = "specialist") -> object:
    """Single-shot call to a specialist that returns JSON (object or array)."""
    print(f"  [Agent: {agent_name}] Processing...")
    result = await agent.run(json.dumps(payload, ensure_ascii=False))
    print(f"  [Agent: {agent_name}] Done.\n")
    return json.loads(_extract_json(result.text))


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

async def run_workflow(bypass_hitl: bool = False) -> None:
    project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
    user_principal = (
        os.environ.get("USER_PRINCIPAL")
        or input("Your name / UPN (for the approved_by field): ").strip()
        or "workshop@local"
    )

    async with DefaultAzureCredential() as credential:
        async with AIProjectClient(
            endpoint=project_endpoint, credential=credential
        ) as projects:
            _hdr("Resolving hosted Foundry agents")
            intake = FoundryAgent(project_client=projects, agent_name=INTAKE_AGENT)
            classifier = FoundryAgent(project_client=projects, agent_name=CLASSIFIER_AGENT)
            drafter = FoundryAgent(project_client=projects, agent_name=DRAFTER_AGENT)
            print(
                f"  ok  -> {INTAKE_AGENT}, {CLASSIFIER_AGENT}, {DRAFTER_AGENT}"
            )

            # 1. Intake (interactive, multi-turn)
            intake_facts_raw = await _interactive_intake(intake)
            intake_facts = IntakeFacts(**intake_facts_raw)
            print(f"\n  Intake captured. case_id={intake_facts.case_id}")

            # 2. Legal classification (single shot)
            _hdr("Step 2 — Legal classification  [handoff -> noclar-legal-classifier]")
            classification_raw = await _call_specialist_json(
                classifier,
                {"intake": intake_facts.model_dump(mode="json")},
                agent_name=CLASSIFIER_AGENT,
            )
            classification = [LegalNormReference(**n) for n in classification_raw]
            print(json.dumps(classification_raw, indent=2, ensure_ascii=False))

            # 3. HITL #1
            if bypass_hitl:
                print("\n[--bypass-hitl] Skipping HITL #1 — proceeding anyway.")
            else:
                ok, comment = _approve_in_terminal(
                    "Classification — proceed to drafting?",
                    [n.model_dump() for n in classification],
                )
                if not ok:
                    print(f"\n[STOP] Classification rejected. Reason: {comment}")
                    return

            # 4. Drafter (single shot)
            _hdr("Step 3 — Draft Initial Assessment Memo  [handoff -> noclar-drafter]")
            memo_raw = await _call_specialist_json(
                drafter,
                {
                    "intake": intake_facts.model_dump(mode="json"),
                    "legal_assessment": [n.model_dump() for n in classification],
                },
                agent_name=DRAFTER_AGENT,
            )
            memo = AssessmentMemo(**memo_raw)
            print(json.dumps(memo.model_dump(mode="json"), indent=2, ensure_ascii=False))

            # 5. HITL #2 — only set approved_by INSIDE the approval branch.
            #    The --bypass-hitl path deliberately leaves it None so the
            #    persist_assessment Function can demonstrate its 409 gate.
            if bypass_hitl:
                print("\n[--bypass-hitl] Skipping HITL #2 — approved_by NOT set.")
            else:
                ok, comment = _approve_in_terminal(
                    "Memo — persist this draft?",
                    memo.model_dump(mode="json"),
                )
                if not ok:
                    print(f"\n[STOP] Memo rejected. Reason: {comment}")
                    return
                memo.approved_by = user_principal
                memo.approved_at = datetime.utcnow()

            # 6. Persist (server-side HITL gate: rejects if approved_by missing)
            _hdr("Step 4 — Persist memo via Function")
            try:
                persist_result = persist_assessment(memo.model_dump(mode="json"))
            except Exception as exc:  # noqa: BLE001 — show the user the raw error
                print(f"  Function call FAILED: {exc!r}")
                print(
                    "  Expected when --bypass-hitl is set: persist_assessment "
                    "returns HTTP 409 because approved_by is missing.\n"
                    "  This is the defense-in-depth gate — the storage layer "
                    "refuses to write a memo that bypassed the human."
                )
                return
            print(json.dumps(persist_result, indent=2))

            # 7. Notify reviewer
            _hdr("Step 5 — Notify reviewer via Function")
            notify_result = notify_reviewer(
                conversation_id=str(uuid.uuid4()),
                case_id=memo.case_id,
                memo_blob_path=persist_result["memo_blob"],
                summary=memo.intake.summary,
                requested_reviewer=os.environ.get("REVIEWER_EMAIL"),
            )
            print(json.dumps(notify_result, indent=2))

            _hdr("Done")
            print(f"  Case:     {memo.case_id}")
            print(f"  Memo:     {persist_result['memo_blob']}")
            print(f"  Approver: {user_principal}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NOCLAR orchestrator (local Python + Agent Framework)."
    )
    parser.add_argument(
        "--bypass-hitl",
        action="store_true",
        help=(
            "Skip both HITL gates and do NOT set approved_by. Used to "
            "demonstrate that persist_assessment returns HTTP 409 even "
            "when the orchestrator misbehaves."
        ),
    )
    args = parser.parse_args()
    try:
        asyncio.run(run_workflow(bypass_hitl=args.bypass_hitl))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
