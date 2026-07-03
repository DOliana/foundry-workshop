# Lab 04 — Voice Interaction & Custom Integration

**Duration:** 60 minutes (Block 4)
**Outcome:** Attach **Azure Functions as agent tools**
(the canonical place for this per the agenda), connect the agent to a
**Microsoft Learn MCP server** to demonstrate dynamic tool discovery,
write a **small custom function tool** of your own, and then watch
an **instructor-led Voice Live demo** that reuses the same agent over
voice.

The voice piece is a **demo**, not an individual build — you watch.
Instructor prep is in [`INSTRUCTOR.md`](./INSTRUCTOR.md).

---

## 1. Uncomment the per-lab files (5 min)

| File | Purpose |
|---|---|
| `src/functions/log_request.py` | Governance-logging Function (Lab 04's home). |
| `src/functions/function_app.py` | Uncomment the `log_request` blueprint registration. |
| `src/labs/lab04/mcp_attach.py` | Prints the Learn MCP URL; can probe `list_tools`. |
| `src/labs/lab04/custom_tool.py` | Stub for your own function tool. |

```bash
python -m py_compile src/functions/log_request.py src/labs/lab04/*.py
azd deploy functions
```

After deploy, the Functions app exposes `log_request` alongside the
Lab 02 handlers.

## 2. Attach `log_request` as an OpenAPI tool on `noclar-intake` (10 min)

In the Foundry portal:

1. **Agents → noclar-intake → Tools → + Add → OpenAPI 3.0 specified
   tool.**
2. Paste [`src/functions/openapi-intake.json`](../../src/functions/openapi-intake.json).
3. Replace the `servers[0].url` placeholder with your Functions
   hostname (`echo $AZURE_FUNCTION_APP_HOSTNAME`).
4. **Authentication:** API key → header → `x-functions-key` →
   paste the key from `az functionapp keys list`.
5. **Save**, then in the Playground send one combined intake
   message (`client_name:` line + tip paragraph in a single send —
   same contract as Lab 01, same contract as Lab 02 orchestrator).
   Include the word **"json"** in the prompt (e.g. start with
   `Extract the IntakeFacts JSON from the intake below.`) — JSON
   response-format mode requires it in the user message.
6. Storage → `logs` container → a new log blob appears.

> **What just happened.** A Foundry agent now calls one of *your*
> HTTP endpoints as a typed tool. The OpenAPI doc is the wire
> contract; the function key is the auth.

## 3. Build an LLM-driven orchestrator agent (10 min)

The Lab 02 orchestrator is deterministic Python. The same Functions
can also be driven by an **LLM-driven agent** for contrast.

1. **+ New agent** → `noclar-orchestrator` → `gpt-5.4-mini`.
2. Paste [`src/labs/prompts/orchestrator.md`](../../src/labs/prompts/orchestrator.md).
3. **Tools → + Add → OpenAPI 3.0 specified tool** →
   [`src/functions/openapi-orchestrator.json`](../../src/functions/openapi-orchestrator.json)
   — same host + function-key flow.
4. Playground: ask it to draft + persist a tiny memo. Watch it call
   `persist_assessment` then `notify_reviewer` in sequence.

> **Same Functions, different driver.** Lab 02's Python orchestrator
> picks tool calls deterministically; this agent picks them with the
> model. Both arrive at the same audit trail.

## 4. Connect an MCP server (10 min)

1. **Agents → noclar-orchestrator → Tools → + Add → MCP server.**
2. **URL:** `https://learn.microsoft.com/api/mcp` (Microsoft Learn
   MCP server).
3. **Save.**
4. Playground: ask *"How do I declare a queue trigger in an Azure
   Functions Python v2 blueprint?"* — observe Learn-MCP tools being
   discovered and called dynamically. No redeploy. No Bicep change.

Optional probe from the CLI:

```bash
python -m src.labs.lab04.mcp_attach --probe
```

## 5. Write a custom function tool (10 min)

Open
[`src/labs/lab04/custom_tool.py`](../../src/labs/lab04/custom_tool.py).
Pick **one** scenario:

- **Scenario A:** `check_sanctions_list(name) -> bool` — returns
  True for a small hard-coded list of counter-parties.
- **Scenario B:** `lookup_engagement(engagement_id) -> dict` —
  returns stub engagement metadata.

Uncomment the matching block and fill in the body. Then either:

- Register it as a **local function tool** through Agent Framework
  for a fast turnaround, or
- Deploy it as a new Functions Blueprint and attach via OpenAPI
  (mirror the steps in §2).

Trigger it from the Playground or a Python smoke script.

## 6. Voice Live demo (10 min — instructor)

> **Prereq:** AAD auth to Voice Live requires two roles on the
> Foundry account (`Cognitive Services User` + `Azure AI User`).
> `scripts/postdeploy-rbac.{ps1,sh}` from Lab 00 grants both. The
> demo connects directly to the realtime *deployment*
> (`gpt-realtime-1.5`) — no separate `noclar-voice-intake` agent
> needed. See [`INSTRUCTOR.md`](./INSTRUCTOR.md).
>
> **Env:** `_log_request` reads `AZURE_FUNCTION_KEY` from `.env`
> (auto-loaded on import). The key is appended to `.env` in
> [Lab 02 §4](../02-orchestration-hitl/README.md#4-set-up-the-venv-and-env-vars-3-min);
> if you skipped Lab 02, append it now or the governance log call
> will silently no-op.

Watch. The instructor:

1. Runs `python -m src.voice.voice_agent_demo`.
2. Speaks the workshop opening line into the mic.
3. The voice agent calls `log_request` (channel=`voice`) and
   responds in speech.
4. The new trace populates Live Metrics on the
   second screen.

If voice fails (regional outage, network block, microphone), the
instructor plays the fallback recording from
[`INSTRUCTOR.md`](./INSTRUCTOR.md).

---

## ✅ Done when

- [ ] `log_request` is deployed and attached as an OpenAPI tool on
      `noclar-intake`. A new log blob appears per intake.
- [ ] `noclar-orchestrator` exists, with `persist_assessment` and
      `notify_reviewer` as OpenAPI tools.
- [ ] The Learn MCP server is attached and you successfully
      triggered a Learn-MCP tool call.
- [ ] Your custom function tool runs from the Playground or a
      scripted call.
- [ ] You watched the voice demo and saw the trace appear in App
      Insights.
