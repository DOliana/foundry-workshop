# Lab 02 — Multi-Agent Orchestration & Human-in-the-Loop

**Duration:** 60 minutes (Block 2)
**Outcome:** A **local Python orchestrator** (Microsoft Agent
Framework) drives three Foundry sub-agents — `noclar-intake`,
`noclar-legal-classifier`, `noclar-drafter` — through a **2-turn
intake**, two HITL approvals in your terminal, and a final
persistence call. When the HITL gate is bypassed, the persistence
Function returns **HTTP 409** — defense in depth.

---

## What is happening and why

```
   you ─type─► orchestrator ─►  noclar-intake          (foundry agent)
                              ─►  noclar-legal-classifier (foundry agent)
                              ─►  HITL #1 in terminal
                              ─►  noclar-drafter        (foundry agent)
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
| [`src/functions/persist_assessment.py`](../../src/functions/persist_assessment.py) | Function: persist approved memo (rejects if not approved). |
| [`src/functions/notify_reviewer.py`](../../src/functions/notify_reviewer.py) | Function: enqueue reviewer notification. |
| [`src/functions/process_reviewer.py`](../../src/functions/process_reviewer.py) | Queue-trigger Function (optional). |
| [`src/functions/function_app.py`](../../src/functions/function_app.py) | Uncomment the **two `app.register_blueprint(...)` lines** for Lab 02. |
| [`src/labs/lab02/orchestrator.py`](../../src/labs/lab02/orchestrator.py) | The Python orchestrator. |
| [`src/labs/lab02/functions_tools.py`](../../src/labs/lab02/functions_tools.py) | httpx wrappers around the Functions HTTP endpoints. |

In VS Code: select the commented block, **Ctrl+/** (toggle line
comment) flips the whole block in one shot.

Compile-check then deploy the Functions code:

```bash
python -m compileall -q src/functions src/labs/lab02
azd deploy functions
```

Run the `azd deploy functions` command from the cloned
`foundry-workshop` root directory — the directory that contains
[`azure.yaml`](../../azure.yaml). If your terminal is in this lab
folder, run `cd ../..` first.

> **What just happened.** `azd deploy functions` packaged the three
> blueprints, pushed them to `func-<suffix>`, and the Functions
> runtime registered the routes.

**Verify in the portal.** Open the Functions app:

```bash
azd env get-value AZURE_FUNCTION_APP_NAME
```

In the [Azure portal](https://portal.azure.com), open the Function
App with that name, then under **Functions → Functions** confirm all
three appear with **Enabled** status:

- `persist_assessment` (HTTP trigger)
- `notify_reviewer` (HTTP trigger)
- `process_reviewer` (Queue trigger on `reviewer-inbox`)

If any are missing, the deploy didn't register the blueprint — check
that you uncommented the matching `app.register_blueprint(...)` lines
in `function_app.py` and re-run `azd deploy functions`.

## 2. Create the two specialist agents in the portal (5 min)

**Build → Agents → + New agent**, twice:

| Field | `noclar-legal-classifier` | `noclar-drafter` |
|---|---|---|
| Model | `gpt-5-mini` | `gpt-5-mini` |
| Response format | **JSON object** | **JSON object** |
| Instructions | paste [`legal_classifier.md`](../../src/labs/prompts/legal_classifier.md) | paste [`drafter.md`](../../src/labs/prompts/drafter.md) |
| Tools | **none** — see callout below | **none** — see callout below |
| Knowledge | none | none |

`noclar-intake` already exists from Lab 01.

> **⚠️ Remove the default Web Search / Grounding tool.** When you
> create a new agent, Foundry attaches a default grounding tool
> (Web Search / Bing Search) automatically. **JSON-object response
> mode is incompatible with Web Search** — the orchestrator will
> die with:
>
> ```
> openai.BadRequestError: Error code: 400 - {'error': {'message':
>   'Web Search cannot be used with JSON mode.', ...}}
> ```
>
> Open each of the three agents (`noclar-intake`,
> `noclar-legal-classifier`, `noclar-drafter`) → **Tools** → delete
> every entry → **Save**. Specialist agents do not need any tools;
> the orchestrator is what calls the Functions.

## 3. Read the orchestrator (5 min)

Open [`src/labs/lab02/orchestrator.py`](../../src/labs/lab02/orchestrator.py).
Spend 5 minutes on it. The file *is* the lab content. Notes:

- `_interactive_intake` — a thin 2-turn driver. Turn 1: client name.
  Turn 2: tip paragraph — read either from `--tip-file PATH` or
  from stdin (multi-line; blank line or `.` ends input). One call
  to `noclar-intake`, one JSON extracted. The driver prepends
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

**Devcontainer / Codespaces:** skip the venv and use plain `pip` —
it installs into your user site (`~/.local`) automatically, which
`uv` does not (`uv pip install --system` tries to write to
`/usr/local/lib/...` and fails as the non-root container user):

```bash
pip install -r src/labs/requirements.txt
```

**Windows native / local Linux / macOS:** use a venv. `uv` works
here because the venv is writable.

bash:

```bash
python -m venv .venv
source .venv/bin/activate
uv pip install -r src/labs/requirements.txt
# if uv is not available: pip install -r src/labs/requirements.txt
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
uv pip install -r src/labs/requirements.txt
# if uv is not available or you are not using a venv: 
# pip install -r src/labs/requirements.txt
```

Smoke check the install:

```bash
python -c "import agent_framework, azure.ai.projects; print('deps ok')"
```

The Foundry endpoint and Functions hostname are already in `.env`
from Lab 00 (`azd env get-values > .env`). Importing `src.labs`
auto-loads that file via `python-dotenv`, so you do **not** need to
source `.env` from your shell.

One value is missing from `.env` — the Functions master key, because
it is not an `azd` output. Append it now:

bash:

```bash
RG=$(azd env get-value AZURE_RESOURCE_GROUP)
APP=$(azd env get-value AZURE_FUNCTION_APP_NAME)
KEY=$(az functionapp keys list -n "$APP" -g "$RG" \
  --query "functionKeys.default" -o tsv)
echo "AZURE_FUNCTION_KEY=$KEY" >> .env
echo "appended AZURE_FUNCTION_KEY=${KEY:0:8}... (masked)"
```

PowerShell:

```powershell
$rg  = (azd env get-value AZURE_RESOURCE_GROUP).Trim()
$app = (azd env get-value AZURE_FUNCTION_APP_NAME).Trim()
$key = (az functionapp keys list -n $app -g $rg `
          --query "functionKeys.default" -o tsv).Trim()
Add-Content -Path .env -Value "AZURE_FUNCTION_KEY=$key"
Write-Host "appended AZURE_FUNCTION_KEY=$($key.Substring(0,8))... (masked)"
```

Spot-check `.env` now contains all three vars the orchestrator
needs: `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT`,
`AZURE_FUNCTION_APP_HOSTNAME`, `AZURE_FUNCTION_KEY`.

> **Why no `export` / `$env:`.** Lab 00 only **writes** `.env`; it
> never sources the values into your shell. Rather than asking you
> to source the file (syntax differs across bash / zsh /
> PowerShell), the lab code auto-loads `.env` on import via
> `python-dotenv` (see `src/labs/__init__.py`). The same applies
> to Labs 03, 04, and 05.

## 5. Happy path (15 min)

The orchestrator can read the tip paragraph from a file (**strongly
recommended** — the fixture is multi-paragraph markdown and pasting
into a terminal is fragile) or from stdin.

From a file (recommended):

```bash
python -m src.labs.lab02.orchestrator --tip-file data/sample-docs/tip.md
```

Interactive (only for short, single-paragraph tips you type by
hand):

```bash
python -m src.labs.lab02.orchestrator
```

Step through:

1. **Client name:** `Contoso Manufacturing` (or anything).
2. **Tip paragraph:** if you used `--tip-file`, this step is
   skipped. Otherwise type the paragraph and finish with a **blank
   line** or `.` on its own line. (Pasting the markdown fixture
   here will fail — use `--tip-file`.)
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
python -m src.labs.lab02.orchestrator --bypass-hitl
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

## 7. Walk the end-to-end trace (5 min)

The orchestrator is instrumented with OpenTelemetry and ships spans
to the App Insights resource that azd provisioned. The Function App
already auto-emits its requests to the same resource, and the
Foundry project is connected to the same App Insights via its
`APPLICATIONINSIGHTS_CONNECTION_STRING` — so a single happy-path run
shows up as **one** end-to-end transaction with a single
`operation_Id`:

```
noclar.lab02.workflow                (orchestrator root span)
├─ azure-ai-projects HTTP            (Foundry agent call: noclar-intake)
├─ azure-ai-projects HTTP            (Foundry agent call: noclar-legal-classifier)
├─ azure-ai-projects HTTP            (Foundry agent call: noclar-drafter)
├─ POST /api/persist_assessment      (httpx → Function request span)
└─ POST /api/notify_reviewer         (httpx → Function request span)
```

**Open the App Insights resource** (Azure portal → your resourcegroup →
your application insights instance → Monitoring → logs): (it might take 1-2 minutes for the function logs to show up as batching occurs during ingestion)

1. Run this Kusto query under **Logs** to find all transactions:
   ```kusto
    union requests, dependencies, traces
    | where timestamp > ago(1h)
    | summarize min(timestamp) by operation_Id
    | order by min_timestamp desc 
   ```
2. Run this to get the details about the transaction using the first operation_id from the previous query
   ```kusto
   union requests, dependencies, traces
   | where operation_Id == "YOUR OPERATION ID"
   | project timestamp, itemType, name, operation_Name, operation_Id, duration, resultCode
   | order by timestamp asc
   ```

**Foundry per-agent traces.** Foundry also keeps a per-agent view
at **Agents → `<agent-name>` → Traces**. That view is scoped to one
agent and is useful for inspecting the system prompt and the JSON
the model returned for a specific run. Use App Insights for the
end-to-end picture, the Foundry view for prompt-level debugging.

**The negative path.** Rerun with `--bypass-hitl`. The same view
shows the 409 — `persist_assessment` is red,
`POST /api/notify_reviewer` is missing (the orchestrator aborts on
the 409), and the request body in custom dimensions confirms
`approved_by` was empty. **App Insights → Failures** picks the same
row up under HTTP 409.

---

## ✅ Done when

- [ ] All three Lab 02 Functions are deployed (visible in the
      portal under your Functions app).
- [ ] Three agents exist in Foundry: `noclar-intake`,
      `noclar-legal-classifier`, `noclar-drafter`.
- [ ] Happy path ran end-to-end; a memo blob with `approved_by` set
      is in `assessments/`.
- [ ] `--bypass-hitl` returned **HTTP 409**.
- [ ] One end-to-end transaction in App Insights shows the
      orchestrator root, three Foundry agent calls, and two Function
      request spans under a single `operation_Id`.

## Discussion (5 min)

- Where would you put HITL gate #3, and why?
- The orchestrator is Python. When would you replace it with an
  **LLM-driven** orchestrator agent? (Lab 04 builds that variant.)
- The two specialists return JSON. What changes if you let them
  return prose?
