"""Lab 02 — local Python orchestrator (simplified 2-turn intake).

Drives three hosted Foundry sub-agents (`noclar-intake`,
`noclar-legal-classifier`, `noclar-drafter`) through a 2-turn intake,
two HITL approvals in the terminal, and a final persistence call that is
rejected (HTTP 409) when the HITL gate is bypassed.

Ships **fully commented**. Lab 02 step 1 uncomments this file.

Run (after uncommenting):

    python -m src.agents.lab02.orchestrator                # full workflow
    python -m src.agents.lab02.orchestrator --bypass-hitl  # negative path

Required env vars:

    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT
        e.g. https://foundry-xxx.services.ai.azure.com/api/projects/noclar-assessment
    AZURE_FUNCTION_APP_HOSTNAME
        e.g. func-noclar-xxx.azurewebsites.net
    AZURE_FUNCTION_KEY
        master key from `az functionapp keys list`
"""

# from __future__ import annotations
#
# import argparse
# import asyncio
# import json
# import os
# import re
# import sys
# import uuid
# from datetime import datetime
#
# from agent_framework.foundry import FoundryAgent
# from azure.ai.projects.aio import AIProjectClient
# from azure.identity.aio import DefaultAzureCredential
#
# from src.agents.lab02.functions_tools import notify_reviewer, persist_assessment
# from src.shared.schemas import AssessmentMemo, IntakeFacts, LegalNormReference
#
# INTAKE_AGENT = "noclar-intake"
# CLASSIFIER_AGENT = "noclar-legal-classifier"
# DRAFTER_AGENT = "noclar-drafter"
#
# _JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
#
#
# def _hdr(label: str) -> None:
#     print("\n" + "=" * 72)
#     print(f"  {label}")
#     print("=" * 72)
#
#
# def _extract_json(text: str) -> str:
#     m = _JSON_FENCE.search(text)
#     return (m.group(1) if m else text).strip()
#
#
# def _approve_in_terminal(label: str, payload: object) -> tuple[bool, str]:
#     _hdr(f"HITL CHECKPOINT — {label}")
#     print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
#     print()
#     answer = input("Approve? Type 'approve' to continue, anything else to reject: ").strip().lower()
#     if answer == "approve":
#         comments = input("Optional comments (press Enter to skip): ").strip()
#         print("  -> APPROVED")
#         return True, comments
#     reason = input("Reason for rejection: ").strip()
#     print("  -> REJECTED")
#     return False, reason
#
#
# def _read_paragraph(prompt_label: str) -> str:
#     """Read a paragraph from stdin. Supports `/paste` ... `/end` for multiline."""
#     print(prompt_label)
#     print("(For multi-line paste, type `/paste`, then the text, then `/end`.)")
#     first = input("You> ").strip()
#     if first.lower() not in ("/paste", "paste"):
#         return first
#     print("Paste mode enabled. End with `/end` on its own line.")
#     lines: list[str] = []
#     while True:
#         try:
#             line = input("... ")
#         except EOFError:
#             break
#         if line.strip().lower() in ("/end", "end"):
#             break
#         lines.append(line)
#     return "\n".join(lines).strip()
#
#
# async def _interactive_intake(intake_agent) -> dict:
#     """Two-turn intake driver.
#
#     Turn 1: ask the user for `client_name`.
#     Turn 2: ask the user to paste the tip paragraph (with /paste mechanic).
#     Then send both as a single user message to the intake agent and parse
#     the JSON it returns.
#     """
#     _hdr("Step 1 — Intake (2-turn)")
#     client_name = input("Client name> ").strip() or "Contoso Manufacturing"
#     tip = _read_paragraph(
#         "\nPaste the tip paragraph (e.g. data/sample-docs/tip.md):"
#     )
#
#     user_message = (
#         "Extract the IntakeFacts JSON from the intake below.\n\n"
#         f"client_name: {client_name}\n\n{tip}"
#     )
#     print(f"\n  [Agent: {INTAKE_AGENT}] Extracting IntakeFacts JSON...")
#     result = await intake_agent.run(user_message)
#     text = _extract_json(result.text)
#     try:
#         facts = json.loads(text)
#     except json.JSONDecodeError as exc:
#         print(f"\n[ERROR] Intake agent did not return valid JSON: {exc}")
#         print(result.text)
#         raise SystemExit(1)
#     facts.setdefault(
#         "case_id",
#         f"INTAKE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
#     )
#     return facts
#
#
# async def _call_specialist_json(agent, payload: dict, agent_name: str) -> object:
#     # Wrap the payload in a natural-language preamble that mentions the
#     # literal word `json`. JSON response-format mode on the agent requires
#     # it in the user message; a bare `json.dumps(...)` body does not
#     # satisfy that check and the API rejects the call.
#     print(f"  [Agent: {agent_name}] Processing...")
#     user_message = (
#         "Process the JSON payload below and return your result as a "
#         "single JSON object matching your output schema.\n\n"
#         + json.dumps(payload, ensure_ascii=False)
#     )
#     result = await agent.run(user_message)
#     print(f"  [Agent: {agent_name}] Done.\n")
#     return json.loads(_extract_json(result.text))
#
#
# async def run_workflow(bypass_hitl: bool = False) -> None:
#     project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
#     user_principal = (
#         os.environ.get("USER_PRINCIPAL")
#         or input("Your name / UPN (for the approved_by field): ").strip()
#         or "workshop@local"
#     )
#
#     async with DefaultAzureCredential() as credential:
#         async with AIProjectClient(endpoint=project_endpoint, credential=credential) as projects:
#             _hdr("Resolving hosted Foundry agents")
#             intake = FoundryAgent(project_client=projects, agent_name=INTAKE_AGENT)
#             classifier = FoundryAgent(project_client=projects, agent_name=CLASSIFIER_AGENT)
#             drafter = FoundryAgent(project_client=projects, agent_name=DRAFTER_AGENT)
#             print(f"  ok  -> {INTAKE_AGENT}, {CLASSIFIER_AGENT}, {DRAFTER_AGENT}")
#
#             intake_facts_raw = await _interactive_intake(intake)
#             intake_facts = IntakeFacts(**intake_facts_raw)
#             print(f"\n  Intake captured. case_id={intake_facts.case_id}")
#
#             _hdr("Step 2 — Legal classification  [handoff -> noclar-legal-classifier]")
#             classification_raw = await _call_specialist_json(
#                 classifier,
#                 {"intake": intake_facts.model_dump(mode="json")},
#                 agent_name=CLASSIFIER_AGENT,
#             )
#             classification = [LegalNormReference(**n) for n in classification_raw]
#             print(json.dumps(classification_raw, indent=2, ensure_ascii=False))
#
#             if bypass_hitl:
#                 print("\n[--bypass-hitl] Skipping HITL #1 — proceeding anyway.")
#             else:
#                 ok, comment = _approve_in_terminal(
#                     "Classification — proceed to drafting?",
#                     [n.model_dump() for n in classification],
#                 )
#                 if not ok:
#                     print(f"\n[STOP] Classification rejected. Reason: {comment}")
#                     return
#
#             _hdr("Step 3 — Draft Initial Assessment Memo  [handoff -> noclar-drafter]")
#             memo_raw = await _call_specialist_json(
#                 drafter,
#                 {
#                     "intake": intake_facts.model_dump(mode="json"),
#                     "legal_assessment": [n.model_dump() for n in classification],
#                 },
#                 agent_name=DRAFTER_AGENT,
#             )
#             memo = AssessmentMemo(**memo_raw)
#             print(json.dumps(memo.model_dump(mode="json"), indent=2, ensure_ascii=False))
#
#             if bypass_hitl:
#                 print("\n[--bypass-hitl] Skipping HITL #2 — approved_by NOT set.")
#             else:
#                 ok, comment = _approve_in_terminal(
#                     "Memo — persist this draft?",
#                     memo.model_dump(mode="json"),
#                 )
#                 if not ok:
#                     print(f"\n[STOP] Memo rejected. Reason: {comment}")
#                     return
#                 memo.approved_by = user_principal
#                 memo.approved_at = datetime.utcnow()
#
#             _hdr("Step 4 — Persist memo via Function")
#             try:
#                 persist_result = persist_assessment(memo.model_dump(mode="json"))
#             except Exception as exc:  # noqa: BLE001
#                 print(f"  Function call FAILED: {exc!r}")
#                 print(
#                     "  Expected when --bypass-hitl is set: persist_assessment "
#                     "returns HTTP 409 because approved_by is missing.\n"
#                     "  Defense in depth — the storage layer refuses what the "
#                     "orchestrator skipped."
#                 )
#                 return
#             print(json.dumps(persist_result, indent=2))
#
#             _hdr("Step 5 — Notify reviewer via Function")
#             notify_result = notify_reviewer(
#                 conversation_id=str(uuid.uuid4()),
#                 case_id=memo.case_id,
#                 memo_blob_path=persist_result["memo_blob"],
#                 summary=memo.intake.summary or memo.intake.tip[:200],
#                 requested_reviewer=os.environ.get("REVIEWER_EMAIL"),
#             )
#             print(json.dumps(notify_result, indent=2))
#
#             _hdr("Done")
#             print(f"  Case:     {memo.case_id}")
#             print(f"  Memo:     {persist_result['memo_blob']}")
#             print(f"  Approver: {user_principal}")
#
#
# def main() -> None:
#     parser = argparse.ArgumentParser(
#         description="NOCLAR orchestrator (local Python + Agent Framework, 2-turn intake)."
#     )
#     parser.add_argument(
#         "--bypass-hitl",
#         action="store_true",
#         help=(
#             "Skip both HITL gates and do NOT set approved_by. Demonstrates "
#             "that persist_assessment returns HTTP 409 when the orchestrator "
#             "misbehaves."
#         ),
#     )
#     args = parser.parse_args()
#     try:
#         asyncio.run(run_workflow(bypass_hitl=args.bypass_hitl))
#     except KeyboardInterrupt:
#         sys.exit(130)
#
#
# if __name__ == "__main__":
#     main()
