# Lab 02 — Multi-Agent Orchestration & Human-in-the-Loop

**Duration:** 60 minutes (Block 2)
**Outcome:** A **local Python orchestrator** (Microsoft Agent
Framework) drives three hosted Foundry sub-agents — `noclar-intake`,
`noclar-legal-classifier`, `noclar-drafter` — through a **2-turn
intake**, two HITL approvals in your terminal, and a final
persistence call. When the HITL gate is bypassed, the persistence
Function returns **HTTP 409** — defense in depth.

---

## What is happening and why

```
   you ─type─► orchestrator ─►  noclar-intake          (hosted agent)
                              ─►  noclar-legal-classifier (hosted agent)
                              ─►  HITL #1 in terminal
                              ─►  noclar-drafter        (hosted agent)
                              ─►  HITL #2 in terminal
                              ─►  persist_assessment    (Azure Function)
                              ─►  notify_reviewer       (Azure Function)
                              ─►  reviewer-inbox queue
                              ─►  process_reviewer      (queue-trigger Function)
```

The orchestrator is **deterministic Python**, not an LLM. It picks
when to call which sub-agent, when to ask the human, and when to
call the Functions. The agents only contribute language work
(extract / classify / draft).

The **negative path** demonstrates that even if the orchestrator
"forgets" the HITL gate, the storage layer still refuses to persist
an unapproved memo. The two gates are independent.

---

## 1. Uncomment the per-lab files (5 min)

These files ship as `# `-prefixed comments. Read each one, then
uncomment.

| File | Purpose |
|---|---|
| `src/functions/persist_assessment.py` | Function: persist approved memo (rejects if not approved). |
| `src/functions/notify_reviewer.py` | Function: enqueue reviewer notification. |
| `src/functions/process_reviewer.py` | Queue-trigger Function (optional). |
| `src/functions/function_app.py` | Uncomment the **two `app.register_blueprint(...)` lines** for Lab 02. |
| `src/agents/lab02/orchestrator.py` | The Python orchestrator. |
| `src/agents/lab02/functions_tools.py` | httpx wrappers around the Functions HTTP endpoints. |

In VS Code: select the commented block, **Ctrl+/** (toggle line
comment) flips the whole block in one shot.

Compile-check then deploy the Functions code:

```bash
python -m py_compile src/functions/*.py src/agents/lab02/*.py
azd deploy functions
```

> **What just happened.** `azd deploy functions` packaged the three
> blueprints, pushed them to `func-<suffix>`, and the Functions
> runtime registered the routes. Browse to the Functions app in the
> portal — under **Functions** you should see `persist_assessment`,
> `notify_reviewer`, `process_reviewer`.

## 2. Create the two specialist agents in the portal (5 min)

**Build → Agents → + New agent**, twice:

| Field | `noclar-legal-classifier` | `noclar-drafter` |
|---|---|---|
| Model | `gpt-4.1-mini` | `gpt-4.1-mini` |
| Response format | **JSON object** | **JSON object** |
| Instructions | paste [`legal_classifier.md`](../../src/agents/prompts/legal_classifier.md) | paste [`drafter.md`](../../src/agents/prompts/drafter.md) |
| Tools / Knowledge | (none) | (none) |

`noclar-intake` already exists from Lab 01.

## 3. Read the orchestrator (5 min)

Open [`src/agents/lab02/orchestrator.py`](../../src/agents/lab02/orchestrator.py).
Spend 5 minutes on it. The file *is* the lab content. Notes:

- `_interactive_intake` — a thin 2-turn driver. Turn 1: client name.
  Turn 2: paragraph (with `/paste` … `/end` for multi-line). One
  call to `noclar-intake`, one JSON extracted. The driver prepends
  `"Extract the IntakeFacts JSON from the intake below."` to the
  user message — JSON response-format mode requires the literal
  word `json` to appear in the user input.
- `_call_specialist_json` — runs a sub-agent. Wraps the payload in a
  short natural-language preamble that mentions `json` (same reason
  as above), strips the optional ```` ```json ```` fence, parses.
- `_approve_in_terminal` — the HITL gate. Type `approve` to
  continue, anything else to abort.
- `run_workflow` — the whole pipeline. The `--bypass-hitl` branch
  skips both gates **and** does not set `approved_by` on the memo,
  which is what triggers the 409 from `persist_assessment`.

## 4. Set up the venv and env vars (3 min)

```bash
python -m venv .venv
source .venv/bin/activate          # bash
# or: .venv\Scripts\Activate.ps1   # PowerShell
pip install -r src/agents/requirements.txt
```

Add the Functions credentials to `.env` (already loaded by the
shell from Lab 00):

```bash
export AZURE_FUNCTION_KEY=$(az functionapp keys list \
  -n $AZURE_FUNCTION_APP_NAME -g $AZURE_RESOURCE_GROUP \
  --query "functionKeys.default" -o tsv)
```

## 5. Happy path (15 min)

```bash
python -m src.agents.lab02.orchestrator
```

Step through:

1. **Client name:** `Contoso Manufacturing` (or anything).
2. **Tip paragraph:** type `/paste`, paste the contents of
   [`data/sample-docs/tip.md`](../../data/sample-docs/tip.md),
   then `/end`.
3. Agent extracts → prints `IntakeFacts`.
4. Orchestrator calls the classifier → prints `LegalNormReference[]`.
5. **HITL #1 — type `approve`.**
6. Orchestrator calls the drafter → prints the `AssessmentMemo`.
7. **HITL #2 — type `approve`.**
8. `persist_assessment` returns 201 with the memo blob path.
9. `notify_reviewer` returns 202.

Open the storage account in the portal → `assessments` container →
your memo is there as `<case_id>/memo-<timestamp>.json`.

## 6. Negative path (5 min)

```bash
python -m src.agents.lab02.orchestrator --bypass-hitl
```

Paste the same fixture. The orchestrator skips both gates, the memo
goes out **without** `approved_by`, and the Function responds:

```
HTTP 409 Conflict
{"error": "memo not approved", "reason": "approved_by is required"}
```

> **The teaching point.** The orchestrator could be wrong. The model
> could be wrong. A future code change could *remove* the terminal
> approval step by accident. The 409 is a hard backstop — the
> storage layer refuses what the orchestrator skipped.

## 7. Walk the traces (5 min)

Foundry → **Tracing → Traces**. The latest happy-path run shows:

- one root span for the orchestrator's local Python run
- three child spans for the hosted sub-agents
- two Function-tool calls at the end

App Insights → **Failures**: the 409 from the bypass run shows up
here, with the request body in the custom dimensions.

---

## ✅ Done when

- [ ] All three Lab 02 Functions are deployed (visible in the
      portal under your Functions app).
- [ ] Three agents exist in Foundry: `noclar-intake`,
      `noclar-legal-classifier`, `noclar-drafter`.
- [ ] Happy path ran end-to-end; a memo blob with `approved_by` set
      is in `assessments/`.
- [ ] `--bypass-hitl` returned **HTTP 409**.
- [ ] You opened one Trace and one Failure in App Insights.

## Discussion (5 min)

- Where would you put HITL gate #3, and why?
- The orchestrator is Python. When would you replace it with an
  **LLM-driven** orchestrator agent? (Lab 04 builds that variant.)
- The two specialists return JSON. What changes if you let them
  return prose?
