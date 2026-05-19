"""Lab 02 — local Python orchestrator (simplified 2-turn intake).

Drives three hosted Foundry sub-agents (`noclar-intake`,
`noclar-legal-classifier`, `noclar-drafter`) through a 2-turn intake,
two HITL approvals in the terminal, and a final persistence call that is
rejected (HTTP 409) when the HITL gate is bypassed.

Ships **fully commented**. Lab 02 step 1 uncomments this file.

Run (after uncommenting):

    python -m src.agents.lab02.orchestrator                                     # interactive
    python -m src.agents.lab02.orchestrator --tip-file data/sample-docs/tip.md  # tip from file
    python -m src.agents.lab02.orchestrator --bypass-hitl                       # negative path

Required env vars:

    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT
        e.g. https://foundry-xxx.services.ai.azure.com/api/projects/noclar-assessment
    AZURE_FUNCTION_APP_HOSTNAME
        e.g. func-noclar-xxx.azurewebsites.net
    AZURE_FUNCTION_KEY
        master key from `az functionapp keys list`
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
from pathlib import Path

from src.agents.lab02.functions_tools import notify_reviewer, persist_assessment
from src.shared.schemas import AssessmentMemo, IntakeFacts, LegalNormReference
from src.shared.telemetry import configure_telemetry

INTAKE_AGENT = "noclar-intake"
CLASSIFIER_AGENT = "noclar-legal-classifier"
DRAFTER_AGENT = "noclar-drafter"


# ---------------------------------------------------------------------------
# Lab 03 §8 — Content Understanding extraction handoff.
# Function ships with the body commented out; uncomment in Lab 03 to call
# the analyzer you built in §6 against the consultancy contract PDF and
# fold the structured result back into `IntakeFacts.documented_facts`.
# ---------------------------------------------------------------------------
def _call_content_understanding(analyzer_id: str, file_path: Path) -> dict:
    """Invoke a Content Understanding analyzer on a local file and return
    the extracted fields as a flat dict (e.g. ``{"parties": "...", "success_fee_percent": 4}``).

    Uses the ``azure-ai-contentunderstanding`` SDK against the Foundry
    account endpoint (``https://<account>.services.ai.azure.com/``) with
    ``DefaultAzureCredential``. Synchronous; the SDK poller handles
    submit + Operation-Location polling for us.
    """
    # --- Lab 03 §8: uncomment this body ---------------------------------
    # from azure.ai.contentunderstanding import ContentUnderstandingClient
    # from azure.identity import DefaultAzureCredential as SyncCredential

    # # The project endpoint looks like
    # #   https://<account>.services.ai.azure.com/api/projects/<project>
    # # Content Understanding lives on the *account* (strip the suffix).
    # project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
    # account_endpoint = project_endpoint.split("/api/projects/", 1)[0].rstrip("/") + "/"

    # client = ContentUnderstandingClient(
    #     endpoint=account_endpoint,
    #     credential=SyncCredential(),
    #     api_version="2025-11-01",
    # )
    # poller = client.begin_analyze_binary(
    #     analyzer_id=analyzer_id,
    #     binary_input=file_path.read_bytes(),
    # )
    # result = poller.result().as_dict()
    # # SDK returns the inner analyze result directly; REST wraps it in
    # # {"status": ..., "result": {...}}. Handle both shapes.
    # inner = result.get("result", result)
    # fields = inner["contents"][0].get("fields", {})
    # return {k: _cu_unwrap(v) for k, v in fields.items()}
    # --- end Lab 03 §8 ---------------------------------------------------
    raise NotImplementedError(
        "Lab 03 §8: uncomment the body of _call_content_understanding "
        "(and the call site in main()) to wire the extraction handoff."
    )


def _cu_unwrap(field: dict) -> object:
    """CU returns ``{"type": "string", "valueString": "..."}`` etc. Pull the value out."""
    for key in (
        "valueString",
        "valueNumber",
        "valueDate",
        "valueBoolean",
        "valueObject",
        "valueArray",
    ):
        if key in field:
            return field[key]
    return field.get("content")

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _hdr(label: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {label}")
    print("=" * 72)


def _extract_json(text: str) -> str:
    m = _JSON_FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _approve_in_terminal(label: str, payload: object) -> tuple[bool, str]:
    _hdr(f"HITL CHECKPOINT — {label}")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    print()
    _flush_stdin()  # discard stray newlines from prior pastes / Enters
    answer = input("Approve? Type 'approve' to continue, anything else to reject: ").strip().lower()
    if answer == "approve":
        _flush_stdin()
        comments = input("Optional comments (press Enter to skip): ").strip()
        print("  -> APPROVED")
        return True, comments
    _flush_stdin()
    reason = input("Reason for rejection: ").strip()
    print("  -> REJECTED")
    return False, reason


def _flush_stdin() -> None:
    """Discard anything still buffered in stdin.

    Terminals deliver a paste as one chunk that `input()` reads
    line-by-line. If the user pasted a multi-line block at a
    paragraph prompt and the read loop terminated on the first blank
    line, the remaining lines stay queued and get consumed by the
    NEXT `input()` call (e.g. the HITL approval prompt) — which
    looks like the orchestrator "reusing the paste" downstream.
    """
    try:
        import termios  # POSIX
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        # Windows path or stdin not a tty (piped input, tests) — nothing to do.
        try:
            import msvcrt  # type: ignore
            while msvcrt.kbhit():
                msvcrt.getch()
        except Exception:
            pass


def _read_paragraph(prompt_label: str) -> str:
    """Read a (possibly multi-line) paragraph from stdin.

    UX: paste or type the paragraph, then finish with either a blank
    line **or** `.` on its own line. Stdin is flushed after the read
    terminates so leftover pasted lines do not poison subsequent
    prompts. For longer inputs prefer `--tip-file PATH`.
    """
    print(prompt_label)
    print("(Paste or type the paragraph. Finish with a blank line or `.` on its own line.)")
    print("(For long / multi-paragraph input, prefer `--tip-file PATH` — see --help.)")
    lines: list[str] = []
    while True:
        try:
            line = input("... " if lines else "You> ")
        except EOFError:
            break
        stripped = line.strip()
        if not lines and not stripped:
            continue
        if stripped in ("", "."):
            break
        lines.append(line)
    _flush_stdin()
    return "\n".join(lines).strip()


async def _interactive_intake(intake_agent, tip_override: str | None = None) -> dict:
    """Two-turn intake driver.

    Turn 1: ask the user for `client_name` (skipped if --tip-file was set
            and the file already contains a `client_name:` line).
    Turn 2: read the tip paragraph (from stdin or `--tip-file`).
    Then send both as a single user message to the intake agent and parse
    the JSON it returns.
    """
    _hdr("Step 1 — Intake (2-turn)")
    client_name = input("Client name> ").strip() or "Contoso Manufacturing"
    if tip_override is not None:
        print(f"\n[--tip-file] using paragraph from file ({len(tip_override)} chars).")
        tip = tip_override
    else:
        tip = _read_paragraph(
            "\nPaste the tip paragraph (e.g. data/sample-docs/tip.md):"
        )

    user_message = (
        "Extract the IntakeFacts JSON from the intake below.\n\n"
        f"client_name: {client_name}\n\n{tip}"
    )
    print(f"\n  [Agent: {INTAKE_AGENT}] Extracting IntakeFacts JSON...")
    result = await intake_agent.run(user_message)
    text = _extract_json(result.text)
    try:
        facts = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"\n[ERROR] Intake agent did not return valid JSON: {exc}")
        print(result.text)
        raise SystemExit(1)
    facts.setdefault(
        "case_id",
        f"INTAKE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
    )
    return facts


async def _call_specialist_json(agent, payload: dict, agent_name: str) -> object:
    # Wrap the payload in a natural-language preamble that mentions the
    # literal word `json`. JSON response-format mode on the agent requires
    # it in the user message; a bare `json.dumps(...)` body does not
    # satisfy that check and the API rejects the call.
    print(f"  [Agent: {agent_name}] Processing...")
    user_message = (
        "Process the JSON payload below and return your result as a "
        "single JSON object matching your output schema.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    result = await agent.run(user_message)
    print(f"  [Agent: {agent_name}] Done.\n")
    raw = result.text or ""
    try:
        return json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] {agent_name} returned invalid JSON: {exc}")
        print(f"[ERROR] Raw response ({len(raw)} chars):\n{raw}\n")
        print(
            "[HINT] If the JSON looks truncated, the agent likely hit its "
            "max output tokens limit. In the Foundry portal, open the agent "
            "and raise 'Max response tokens' (e.g. to 4096) under "
            "Configuration / Advanced settings, then re-run."
        )
        raise


async def run_workflow(bypass_hitl: bool = False, tip_file: str | None = None) -> None:
    # Root span for the whole workflow. Foundry agent calls go through the
    # azure-sdk HTTP pipeline (auto-instrumented by azure-monitor-opentelemetry)
    # and the two Function calls go through httpx (instrumented in
    # configure_telemetry), so both inherit this span's trace context. The
    # Function App and the Foundry project both log to the same App Insights
    # resource, so everything lands under a single operation_Id.
    from datetime import timezone
    from opentelemetry import trace

    tracer = trace.get_tracer("noclar.orchestrator")
    with tracer.start_as_current_span("noclar.lab02.workflow") as root_span:
        root_span.set_attribute("noclar.bypass_hitl", bypass_hitl)
        if tip_file:
            root_span.set_attribute("noclar.tip_file", tip_file)

        # App Insights `operation_Id` == the OTel trace_id formatted as
        # 32 lowercase hex chars. Print it so the participant can paste it
        # straight into a Kusto filter, plus UTC start/end timestamps for
        # `timestamp between(...)` queries.
        trace_id = trace.format_trace_id(root_span.get_span_context().trace_id)
        started_at = datetime.now(timezone.utc)
        _hdr("Trace")
        print(f"  operation_Id : {trace_id}")
        print(f"  started_utc  : {started_at.isoformat(timespec='seconds')}")

        try:
            await _run_workflow_inner(bypass_hitl=bypass_hitl, tip_file=tip_file)
        finally:
            ended_at = datetime.now(timezone.utc)
            _hdr("Trace (end)")
            print(f"  operation_Id : {trace_id}")
            print(f"  started_utc  : {started_at.isoformat(timespec='seconds')}")
            print(f"  ended_utc    : {ended_at.isoformat(timespec='seconds')}")
            print(f"  duration_s   : {(ended_at - started_at).total_seconds():.2f}")
            print(
                "\n  App Insights → Logs:\n"
                "    union requests, dependencies, traces, exceptions\n"
                f"    | where operation_Id == \"{trace_id}\"\n"
                "    | order by timestamp asc"
            )


async def _run_workflow_inner(bypass_hitl: bool = False, tip_file: str | None = None) -> None:
    project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
    user_principal = (
        os.environ.get("USER_PRINCIPAL")
        or input("Your name / UPN (for the approved_by field): ").strip()
        or "workshop@local"
    )
    tip_override: str | None = None
    if tip_file:
        from pathlib import Path
        tip_override = Path(tip_file).read_text(encoding="utf-8").strip()

    async with DefaultAzureCredential() as credential:
        async with AIProjectClient(endpoint=project_endpoint, credential=credential) as projects:
            _hdr("Resolving hosted Foundry agents")
            intake = FoundryAgent(project_client=projects, agent_name=INTAKE_AGENT)
            classifier = FoundryAgent(project_client=projects, agent_name=CLASSIFIER_AGENT)
            drafter = FoundryAgent(project_client=projects, agent_name=DRAFTER_AGENT)
            print(f"  ok  -> {INTAKE_AGENT}, {CLASSIFIER_AGENT}, {DRAFTER_AGENT}")

            intake_facts_raw = await _interactive_intake(intake, tip_override=tip_override)
            intake_facts = IntakeFacts(**intake_facts_raw)

            # --- Lab 03 §8: uncomment this block --------------------------
            # Calls the `consultancy-contract` Content Understanding analyzer
            # against the contract PDF, prints the extracted fields, and
            # appends a single evidence bullet to `documented_facts` so the
            # downstream drafter picks it up in Section 3 of the memo.
            # cu_fields = _call_content_understanding(
            #     analyzer_id="consultancycontract",
            #     file_path=Path("data/sample-docs/contract-excerpt-consultancy.pdf"),
            # )
            # print("\n  Content Understanding extracted:")
            # print(json.dumps(cu_fields, indent=2, ensure_ascii=False))
            # intake_facts.documented_facts.append(
            #     f"Consultancy agreement with {cu_fields.get('parties', '?')} "
            #     f"(effective {cu_fields.get('effective_date', '?')}, "
            #     f"governed by {cu_fields.get('governing_law', '?')} law) sets "
            #     f"a monthly retainer plus a "
            #     f"{cu_fields.get('success_fee_percent', '?')}% success fee, "
            #     f"with deliverable-acceptance-before-payment = "
            #     f"{cu_fields.get('deliverable_required_before_payment', '?')} "
            #     "(source: contract-excerpt-consultancy; "
            #     "extracted_by: content-understanding/consultancy-contract)."
            # )
            # --------------------------------------------------------------

            print(json.dumps(intake_facts.model_dump(mode="json"), indent=2, ensure_ascii=False))
            print(f"\n  Intake captured. case_id={intake_facts.case_id}")

            _hdr("Step 2 — Legal classification  [handoff -> noclar-legal-classifier]")
            classification_raw = await _call_specialist_json(
                classifier,
                {"intake": intake_facts.model_dump(mode="json")},
                agent_name=CLASSIFIER_AGENT,
            )
            # Classifier returns {"norms": [...]} — the top-level object is
            # required by JSON-object response mode. Accept a raw list as a
            # fallback in case the agent ignores the wrapper.
            if isinstance(classification_raw, dict):
                norms_list = classification_raw.get("norms", [])
            elif isinstance(classification_raw, list):
                norms_list = classification_raw
            else:
                norms_list = []
            if not norms_list:
                print(
                    "\n[WARN] Classifier returned no norms. Raw payload:\n"
                    f"{json.dumps(classification_raw, indent=2, ensure_ascii=False)}"
                )
            classification = [LegalNormReference(**n) for n in norms_list]
            print(json.dumps([n.model_dump() for n in classification], indent=2, ensure_ascii=False))

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

            _hdr("Step 4 — Persist memo via Function")
            hostname = os.environ.get("AZURE_FUNCTION_APP_HOSTNAME", "<unset>")
            print(f"  -> POST https://{hostname}/api/persist_assessment")
            try:
                persist_result = persist_assessment(memo.model_dump(mode="json"))
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                is_dns = "Name or service not known" in msg or "getaddrinfo" in msg
                is_conn = "ConnectError" in repr(exc) or "ConnectionError" in repr(exc)
                print(f"  Function call FAILED: {exc!r}")
                if is_dns or is_conn:
                    hostname = os.environ.get("AZURE_FUNCTION_APP_HOSTNAME", "<unset>")
                    print(
                        f"\n  [HINT] Could not reach the Function App at: {hostname}\n"
                        "  This is almost always a stale env var. Fix:\n"
                        "    azd env get-value AZURE_FUNCTION_APP_HOSTNAME\n"
                        "    az functionapp list -g $AZURE_RESOURCE_GROUP \\\n"
                        "      --query \"[].defaultHostName\" -o tsv\n"
                        "  If they differ, re-export:\n"
                        "    export AZURE_FUNCTION_APP_HOSTNAME=$(az functionapp list \\\n"
                        "      -g $AZURE_RESOURCE_GROUP --query \"[0].defaultHostName\" -o tsv)\n"
                        "    export AZURE_FUNCTION_KEY=$(az functionapp keys list \\\n"
                        "      -g $AZURE_RESOURCE_GROUP -n <func-name> \\\n"
                        "      --query masterKey -o tsv)"
                    )
                elif bypass_hitl:
                    print(
                        "  Expected when --bypass-hitl is set: persist_assessment "
                        "returns HTTP 409 because approved_by is missing.\n"
                        "  Defense in depth — the storage layer refuses what the "
                        "orchestrator skipped."
                    )
                return
            print(json.dumps(persist_result, indent=2))

            _hdr("Step 5 — Notify reviewer via Function")
            print(f"  -> POST https://{hostname}/api/notify_reviewer")
            notify_result = notify_reviewer(
                conversation_id=str(uuid.uuid4()),
                case_id=memo.case_id,
                memo_blob_path=persist_result["memo_blob"],
                summary=memo.intake.summary or memo.intake.tip[:200],
                requested_reviewer=os.environ.get("REVIEWER_EMAIL"),
            )
            print(json.dumps(notify_result, indent=2))

            _hdr("Done")
            print(f"  Case:     {memo.case_id}")
            print(f"  Memo:     {persist_result['memo_blob']}")
            print(f"  Approver: {user_principal}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NOCLAR orchestrator (local Python + Agent Framework, 2-turn intake)."
    )
    parser.add_argument(
        "--bypass-hitl",
        action="store_true",
        help=(
            "Skip both HITL gates and do NOT set approved_by. Demonstrates "
            "that persist_assessment returns HTTP 409 when the orchestrator "
            "misbehaves."
        ),
    )
    parser.add_argument(
        "--tip-file",
        default=None,
        help=(
            "Read the tip paragraph from a file instead of stdin. Avoids "
            "paste-handling quirks in some terminals. "
            "Example: --tip-file data/sample-docs/tip.md"
        ),
    )
    args = parser.parse_args()
    configure_telemetry("noclar-orchestrator")
    try:
        asyncio.run(run_workflow(bypass_hitl=args.bypass_hitl, tip_file=args.tip_file))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
