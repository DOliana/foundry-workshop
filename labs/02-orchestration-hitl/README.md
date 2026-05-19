# Lab 02 — Multi-Agent Orchestration & Human-in-the-Loop

**Block 2 · 60 min**
**Outcome:** A local Python orchestrator (built on **Microsoft Agent Framework**) that drives `noclar-intake`, `noclar-legal-classifier`, and `noclar-drafter` as hosted Foundry sub-agents, enforces two HITL checkpoints in your terminal, and persists the final memo via `persist_assessment` — with the persistence Function refusing any memo that bypasses the human gate.

---

## What you do here and why

In Lab 01 you built one agent with one tool. The real NOCLAR workflow is a **multi-step pipeline with two mandatory human approvals**:

1. **HITL #1** — confirm the legal classification before drafting.
2. **HITL #2** — approve the drafted memo before it is persisted.

This lab introduces three new things:

- **Two more Functions** (`persist_assessment`, `notify_reviewer`) — including the persistence-layer **HITL gate** (Function returns `409` if `approved_by` is missing). This is defense in depth: even if the orchestrator skips the prompt, the storage layer refuses.
- **Two more specialist agents** (`noclar-legal-classifier`, `noclar-drafter`) — created in the Foundry portal the same way as the intake agent in Lab 01.
- **Microsoft Agent Framework** — a Python orchestration library that fetches your hosted Foundry agents by name and drives them with deterministic Python code. The specialist agents stay in the portal so the prompt team can iterate on them; the *workflow* lives in [`../../src/agents/orchestrator.py`](../../src/agents/orchestrator.py) where it can be unit-tested and traced.

The HITL prompts happen **in your terminal**: the script prints the classification (or memo) and you type `approve` / a rejection reason. No webhook, no Teams card — the workshop-grade UX is stdin. The shape is identical to what you'd ship: in production the stdin prompts become Teams adaptive cards or web modals, and the script becomes a Durable Function, but the orchestrator code looks the same.

---

## 1. Enable the new Function handlers (5 min)

Open [`../../src/functions/function_app.py`](../../src/functions/function_app.py). Three blocks need to come alive for this lab. For each, remove the leading `# ` from every code line in the block (keep the comment header lines as comments):

| Block | Why |
| --- | --- |
| `# --- BEGIN _queue_client ---` | The shared queue client used by `notify_reviewer`. |
| `# --- BEGIN persist_assessment ---` | Writes the approved memo to the `assessments` container. Enforces the `approved_by` gate. |
| `# --- BEGIN notify_reviewer ---` | Enqueues a reviewer notification on `reviewer-inbox`. |

Optional: also uncomment `# --- BEGIN process_reviewer ---` — it's a queue-trigger handler that simply logs notifications to App Insights so you can see them in Traces. Not called by any agent; runs automatically when `notify_reviewer` writes a message.

Save the file. Quick sanity check (pure syntax check — no packages required):

```bash
python -m py_compile src/functions/function_app.py
```

No output = good. (If you have a venv with the Function App's `requirements.txt` installed you can also run `python -c "import function_app"` from `src/functions/`, but `azd deploy functions` will surface any real import error anyway.)

## 2. Re-deploy the Functions code (3 min)

```bash
azd deploy functions
```

Same command you ran in Lab 01. This re-packages [`src/functions/`](../../src/functions/) with the now-uncommented handlers and pushes it. Expect ~2 min.

After it finishes, verify the new endpoints exist.

PowerShell:

```powershell
$func = (azd env get-value AZURE_FUNCTION_APP_NAME).Trim()
$rg   = (azd env get-value AZURE_RESOURCE_GROUP).Trim()
az functionapp function list --name $func --resource-group $rg --query "[].name" -o tsv
```

bash / zsh:

```bash
func=$(azd env get-value AZURE_FUNCTION_APP_NAME)
rg=$(azd env get-value AZURE_RESOURCE_GROUP)
az functionapp function list --name "$func" --resource-group "$rg" --query "[].name" -o tsv
```

You should see **four** entries: `log_request`, `persist_assessment`, `notify_reviewer`, `process_reviewer` (the last only if you uncommented it).

## 3. Create the `noclar-legal-classifier` agent (5 min)

In the Foundry portal (same project from Lab 00 — use `azd env get-value AZURE_AI_FOUNDRY_PORTAL_URL` if you've lost the tab):

1. **Build → Agents → + New agent**.
2. **Name:** `noclar-legal-classifier`
3. **Deployment:** `gpt-4.1-mini`
4. **Instructions:** paste the contents of [`../../src/agents/prompts/legal_classifier.md`](../../src/agents/prompts/legal_classifier.md).
5. Leave **Tools** empty (delete web search).
6. **Response format:** set to **JSON object** (in the agent's *Output* / *Response format* settings). Together with the prompt's explicit JSON example, this guarantees the orchestrator can parse the classifier's output without "explanation prose plus a code fence" surprises.
7. **Save**.

This agent has no tools — it's a pure JSON-shaped classifier. Output is an array of `LegalNormReference` objects (statute, elements of offence, risk class, confidence).

> **Two layers of JSON enforcement.** The prompt contains a worked example (cheap, improves first-token routing). The *Response format* toggle constrains the decoder (guarantees valid JSON regardless of prompt drift). Use both whenever a sub-agent's output is consumed by another agent or by code. If your Foundry build supports **JSON schema** (strict mode) in addition to plain **JSON object**, prefer schema mode and paste the per-element schema from the classifier prompt — but plain JSON object is enough for the workshop.

## 4. Create the `noclar-drafter` agent (5 min)

Same flow:

1. **+ New agent**.
2. **Name:** `noclar-drafter`
3. **Deployment:** `gpt-4.1-mini`
4. **Instructions:** paste [`../../src/agents/prompts/drafter.md`](../../src/agents/prompts/drafter.md).
5. Leave **Tools** empty.
6. **Response format:** **JSON object** (same toggle as the classifier in step 3). The drafter's output is the largest and most nested of the three sub-agents (`AssessmentMemo` has ~10 top-level fields including a nested `IntakeFacts` and an array of legal norms), so enforcing valid JSON at decode time is critical — the `persist_assessment` Function will reject anything it can't parse, and you don't want to discover a stray markdown fence at HITL #2.
7. **Save**.

Also tool-less — pure text/JSON generation following the memo template at [`../../data/memo-template/template.md`](../../data/memo-template/template.md).

> **Workshop vs production.** This drafter prompt is deliberately LLM-heavy so you can read it end-to-end. In a real product you would: (1) inject the memo template as File Search context instead of referencing it by path, (2) ground IDW PS 210 / ISA 250 paragraphs via Azure AI Search instead of relying on training knowledge (Lab 03), (3) move deterministic rules out of the prompt — e.g. escalation list computed from `materiality_judgement` in `persist_assessment`, not by the LLM, (4) switch Response format from *JSON object* to **JSON schema (strict)** using the Pydantic-generated schema, (5) add evaluators for forbidden language and hallucinated persons/sums (Lab 05), and (6) deploy the prompt as code via SDK/Bicep with golden-set regression tests. The current prompt is fine for a 60-minute lab; do not ship it to a partner.

## 5. Install the orchestrator and set up `.env` (5 min)

This lab's orchestrator is a local Python script at [`../../src/agents/orchestrator.py`](../../src/agents/orchestrator.py) built on **Microsoft Agent Framework**. It resolves the three hosted agents you just created by name and drives them with plain Python.

From the repo root (`foundry-workshop/`):

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r src/agents/requirements.txt
```

bash / zsh:

```bash
python -m venv .venv
source .venv/bin/activate
uv pip install -r src/agents/requirements.txt
```

Now create a `.env` at the repo root with the three values the orchestrator needs. PowerShell one-liner:

```powershell
@"
AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=$((azd env get-value AZURE_AI_FOUNDRY_PROJECT_ENDPOINT).Trim())
AZURE_FUNCTION_APP_HOSTNAME=$((azd env get-value AZURE_FUNCTION_APP_HOSTNAME).Trim())
AZURE_FUNCTION_KEY=$(az functionapp keys list --name (azd env get-value AZURE_FUNCTION_APP_NAME).Trim() --resource-group (azd env get-value AZURE_RESOURCE_GROUP).Trim() --query masterKey -o tsv)
"@ | Out-File -Encoding ascii .env
```

bash / zsh:

```bash
cat > .env <<EOF
AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=$(azd env get-value AZURE_AI_FOUNDRY_PROJECT_ENDPOINT)
AZURE_FUNCTION_APP_HOSTNAME=$(azd env get-value AZURE_FUNCTION_APP_HOSTNAME)
AZURE_FUNCTION_KEY=$(az functionapp keys list --name $(azd env get-value AZURE_FUNCTION_APP_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query masterKey -o tsv)
EOF
```

Load it into your current shell (PowerShell):

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') }
}
```

bash / zsh:

```bash
set -a; source .env; set +a
```

Make sure you're logged in for `DefaultAzureCredential`:

```bash
az login
```

## 6. Read the orchestrator before you run it (5 min)

Open [`../../src/agents/orchestrator.py`](../../src/agents/orchestrator.py) and read it top-to-bottom. It's ~250 lines and is the *content* of this lab — the rest of the lab is just walking it through. Things to notice:

- **`AzureAIProjectAgentProvider.get_agent(agent_name=...)`** — fetches a *hosted* Foundry agent by its portal name. No re-creating agents in code; the three agents you just built in steps 3–5 (plus the intake agent from Lab 01) live in the portal.
- **`_interactive_intake`** — multi-turn conversation with the intake sub-agent, using a server-side thread (`agent.get_new_thread()`). Each user line is sent via `agent.run(msg, thread=thread)`; the agent's reply prints back. When you type `done`, the orchestrator asks the agent for its final `IntakeFacts` JSON.
- **`_call_specialist_json`** — single-shot call for classifier and drafter (`agent.run(json_payload)`), parses the JSON response with `_extract_json` (which tolerates stray markdown fences as a belt-and-braces measure on top of the *Response format = JSON object* toggle).
- **HITL gates** — `_approve_in_terminal(...)` prints the payload, reads `approve` / anything else from stdin, returns `(ok, comment)`. The orchestrator returns early on reject.
- **`approved_by` is only set inside the HITL-approved branch.** If you skip the approval, the field stays `None` and the Function refuses the persist — that's the defense-in-depth gate (step 8).
- **No LLM orchestrator agent.** The workflow shape is deterministic Python; the LLMs only do the work *inside* each step.

## 7. Run the workflow end-to-end (15 min)

From the repo root, with the venv active and `.env` loaded:

```bash
python -m src.agents.orchestrator
```

The script will:

1. Resolve the three hosted agents by name.
2. Start the intake conversation. Use this opener (you can paste it):

   > I am Senior Manager Mara Lehmann. The matter concerns Helios Industrieanlagen GmbH — anonymous tip about possible improper advisor payments via Adriatic Advisory in HR/BiH. I will paste two intake emails next.

   Then open [`../../data/sample-docs/intake-email-01-anonymous-tip.md`](../../data/sample-docs/intake-email-01-anonymous-tip.md) and [`../../data/sample-docs/intake-email-02-internal-whistleblower.md`](../../data/sample-docs/intake-email-02-internal-whistleblower.md) and **paste their contents** into the next `You>` prompts, one at a time. The hosted Foundry agent has no filesystem access — it can only see what you type.

   The intake agent will call `log_request` (governance hook from Lab 01) on the first turn and then ask follow-up questions. Answer briefly. When you've covered the facts, type `done` — the agent will emit a final `IntakeFacts` JSON object and the script will parse it.

3. Call `noclar-legal-classifier` with the intake facts. Prints 1–3 norms.
4. **HITL #1** — script prints the classification and prompts. Type `approve`.
5. Call `noclar-drafter` with intake + confirmed classification. Prints the full memo.
6. **HITL #2** — script prints the memo and prompts. Type `approve`.
7. Call `persist_assessment` with `approved_by` = your UPN. Function returns `201` with `memo_blob`.
8. Call `notify_reviewer` with the memo blob path. Function returns `202`.
9. Prints a final summary: case id, memo blob path, approver.

Sanity check the persisted memo:

```powershell
$account = (azd env get-value AZURE_STORAGE_ACCOUNT).Trim()
az storage blob list --account-name $account --container-name assessments --auth-mode login --query "[].name" -o tsv
```

Pick the blob path from the summary and download it:

```powershell
$blob = "<paste the memo_blob path here>"
az storage blob download --account-name $account --container-name assessments --name $blob --file ./memo.json --auth-mode login
code ./memo.json
```

Compare to [`../../data/memo-template/example-helios.md`](../../data/memo-template/example-helios.md).

## 8. Negative path — bypass the HITL gate (5 min)

The orchestrator's `--bypass-hitl` flag skips both terminal prompts and (critically) does **not** set `approved_by`. This is what would happen if the script were buggy, the prompt drifted, or someone forked the orchestrator and removed the approval calls.

```bash
python -m src.agents.orchestrator --bypass-hitl
```

Walk through intake the same way as in step 7, type `done`. The script proceeds straight through the classifier and drafter without prompting, then attempts to persist. Expected:

```
Step 4 — Persist memo via Function
  Function call FAILED: HTTPStatusError('Client error 409 Conflict for url ...')
  Expected when --bypass-hitl is set: persist_assessment returns HTTP 409
  because approved_by is missing.
  This is the defense-in-depth gate — the storage layer refuses to write
  a memo that bypassed the human.
```

The Function returns `409` with body `{"error": "memo missing approved_by — HITL gate not satisfied"}`.

This is the takeaway: **the persistence layer enforces the gate independently of the orchestrator.** Two layers — Python + Function. Either one alone is necessary but not sufficient; both together is the production posture.

## 9. Open Traces (5 min)

The hosted-agent runs (intake / classifier / drafter) are recorded by **Foundry Tracing** because they execute server-side via the project endpoint. In the portal: **Tracing → Recent runs → click your full-workflow run**.

You should see:

- One run per sub-agent call — `noclar-intake` will show multiple LLM spans (one per turn of the conversation) and a tool call for `log_request`. `noclar-legal-classifier` and `noclar-drafter` will each show a single LLM span.
- For the bypass run: the same intake / classifier / drafter spans, but no record of `persist_assessment` succeeding (the Function returned 409, surfaced in your terminal). Open App Insights → *Failures* on the Function App to see the 409 from the server side.

Agent Framework also supports OpenTelemetry export — wire it to App Insights with `agent_framework.observability.setup_observability()` if you want the Python orchestrator's spans (the wrapper around each `agent.run()` plus the HITL gate timings) in the same Application Map as your Functions. Out of scope for this lab; revisit when you take this back to a real engagement.

## ✅ Done when

- [ ] All four Function handlers are deployed (`log_request`, `persist_assessment`, `notify_reviewer`, `process_reviewer`).
- [ ] Two new agents exist in the project: `noclar-legal-classifier`, `noclar-drafter` (with **Response format = JSON object** on both).
- [ ] You ran `python -m src.agents.orchestrator` end-to-end and approved at HITL #1 *and* HITL #2 in the terminal.
- [ ] A persisted memo blob exists in `assessments/`.
- [ ] `python -m src.agents.orchestrator --bypass-hitl` returned 409 from `persist_assessment`.
- [ ] Traces in the portal show the three sub-agent runs.

## Discussion (5 min wrap-up)

- Today the orchestrator runs in your terminal and the HITL prompts are stdin. For a partner-level reviewer at EY, where should this live in production — Teams adaptive card, Outlook approval, dedicated web app? Which parts of [`orchestrator.py`](../../src/agents/orchestrator.py) change, and which stay the same?
- We enforced the HITL gate in *both* the Python orchestrator and the `persist_assessment` Function. Where else should we add defense-in-depth (Search index ACLs? Logic App approval? Conditional Access on the Function App?).
- Agent Framework lets you swap the orchestrator's transport (sync Python today, Durable Function tomorrow, Logic App workflow next) without changing the sub-agents. What does that imply for how the prompt team and the platform team divide ownership?

---

## Reference

- Orchestrator: [`src/agents/orchestrator.py`](../../src/agents/orchestrator.py) — the lab content
- Prompts: [`src/agents/prompts/legal_classifier.md`](../../src/agents/prompts/legal_classifier.md), [`drafter.md`](../../src/agents/prompts/drafter.md)
- Function source: [`src/functions/function_app.py`](../../src/functions/function_app.py) → `persist_assessment`, `notify_reviewer`, `process_reviewer`
- HTTP wrappers (httpx): [`src/agents/tools/functions_tools.py`](../../src/agents/tools/functions_tools.py)
- Memo template: [`data/memo-template/template.md`](../../data/memo-template/template.md)
