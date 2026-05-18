# Lab 04 — Voice Interaction & Custom Integration

**Block 4 · 14:45 – 16:00 (50 min lab)**
**Outcome:** The pre-deployed Functions are wired as agent tools, the reviewer queue carries an end-to-end approval, and you have done a short live voice intake.

---

## Why this matters

A useful NOCLAR agent needs to reach beyond the model:

- **Functions as tools** — persist results, write the governance log, route HITL requests.
- **Voice** — many intake conversations happen on the phone; the same agent must work in that channel without re-training.
- **MCP** — dynamic tool discovery so we don't have to redeploy every time a new internal API appears.

## Pre-conditions

- Labs 00–03 done.
- `azd deploy functions` has been run (or `./scripts/deploy-functions.ps1`).

## Steps

### 1. Confirm the Functions are live (5 min)

```bash
$host = (azd env get-value AZURE_FUNCTION_APP_HOSTNAME).Trim()
curl "https://$host/api/log_request" -X POST -H "content-type: application/json" -d '{"channel":"chat","conversation_id":"test-001"}'
```

Expect HTTP 201 with a `log_blob` path. Confirm the blob lands in Storage:

```bash
$account = (azd env get-value AZURE_STORAGE_ACCOUNT).Trim()
az storage blob list --account-name $account --container-name logs --auth-mode login --query "[].name" -o tsv
```

### 2. Register the Functions as tools on the orchestrator (10 min)

The `noclar-orchestrator` already has function-tool *signatures* from the seed script. Verify by opening **Agents → noclar-orchestrator → Tools** in the portal — you should see:

- `log_request`
- `persist_assessment`
- `notify_reviewer`

If any are missing, re-run `python scripts/seed_foundry_project.py`.

### 3. End-to-end reviewer flow (10 min)

Re-run the Lab 02 orchestrator script. After approving the memo, watch the reviewer queue process the notification:

```bash
$logws = (azd env get-value AZURE_LOG_ANALYTICS_WORKSPACE_NAME).Trim()
az monitor log-analytics query -w $logws --analytics-query "traces | where message has 'Reviewer queue received' | take 10"
```

You should see your reviewer payload logged by the `process_reviewer` queue trigger.

### 4. Add a new function tool yourself (15 min)

Pick one of:

- `check_sanctions_list(name: str)` — returns `True` if a person/company is on a configured list.
- `lookup_engagement(engagement_id: str)` — returns engagement metadata.

Implementation hint:

1. Add a Python function in `src/functions/function_app.py`.
2. Re-deploy with `./scripts/deploy-functions.ps1`.
3. Add a corresponding wrapper in `src/agents/tools/functions_tools.py`.
4. In the portal, attach the new tool to `noclar-orchestrator`.
5. Ask the orchestrator a question that should trigger it.

### 5. Voice intake demo (10 min)

> This is a demo, not an individual build. Watch the instructor first, then try.

Instructor (or one volunteer) runs:

```bash
pip install -r src/voice/requirements.txt
python -m src.voice.voice_agent_demo
```

Speak the same opening line as in Lab 01. The voice agent:

- Calls `log_request` (channel="voice") — confirm with a tail of the `logs/` container.
- Reads back what it heard.
- Asks the next intake question.

> If the voice SDK is unavailable in your subscription region, the instructor will substitute a recording.

## ✅ Done when

- [ ] You have called `log_request` over HTTP and seen a blob land.
- [ ] You have observed the reviewer queue process at least one message.
- [ ] You have added one new function tool and triggered it from the agent.
- [ ] You have heard the voice demo end-to-end.

## Discussion

- The voice channel reuses the same agent definition. What does this imply for how prompts must be written?
- How would you persist a structured voice intake — same `persist_assessment` Function, or a different ingestion path?
