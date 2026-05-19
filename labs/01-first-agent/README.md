# Lab 01 — Your First Agent + Functions as Tools

**Block 1 · 60 min**
**Outcome:** A `noclar-intake` agent you created by hand in the Foundry portal, talking to a `log_request` Azure Function tool you deployed yourself, with the round-trip visible in Traces.

---

## What you do here and why

This lab introduces **Azure Functions** as the way an agent does side effects (here: writing a governance audit log). You will:

1. Build the agent first, in the portal, with no tools — so you see what a plain Foundry agent does.
2. Deploy the Functions code into the empty Function App that Lab 00 provisioned.
3. Attach `log_request` as an OpenAPI tool on your agent and watch the agent call it on every conversation.

Order matters: plain agent → deploy infra code → attach tool. That way, when Traces shows the `log_request` span in step 7, you know exactly what you wired and why.

---

## 1. Open your Foundry project (2 min)

Use script below to get deep link or move manually through [AI foundry portal](https://ai.azure.com)

```bash
azd env get-value AZURE_AI_FOUNDRY_PORTAL_URL
```

Open the URL. Confirm:

- Project `noclar-assessment` is selected.
- **Build → Agents** is empty (you'll fix that in step 2).
- **My assets → Models + endpoints** shows `gpt-4.1-mini`.

## 2. Create the `noclar-intake` agent — no tools yet (10 min)

In the portal:

1. **Build → Agents → + New agent**.
2. **Name:** `noclar-intake`
3. **Deployment:** select `gpt-4.1-mini`.
4. **Instructions:** open [`../../src/agents/prompts/intake.md`](../../src/agents/prompts/intake.md), copy the whole file content, paste it into the Instructions box.
   - Yes, the prompt mentions a `log_request` tool. The agent will *want* to call it but won't be able to yet. That's intentional — you will see the failure mode in step 3, then fix it in step 6.
5. Leave **Tools** empty for now.
6. **Response format:** leave on **Text** (the default). The intake agent is *conversational* — every turn except the final handoff is plain English Q&A, so we cannot force JSON-object mode here without breaking the dialog. The prompt instructs the model to emit a single `IntakeFacts` JSON object only at the final handoff turn (with an explicit worked example). This is the trade-off compared to the classifier and drafter in Lab 02, where decoder-level JSON enforcement *is* possible because those agents only ever produce one response.
7. **Save**.

You now have one agent. The portal will show it with no tools attached.

## 3. Test the agent in the Playground (8 min)

Click **Try in playground** on the agent.

Send a typical intake opener, for example:

> Hello, I am Senior Manager Mara Lehmann. We have received an anonymous tip regarding potential bribery payments via a consultant in Croatia.

Observe:

- The agent greets you and starts asking structured intake questions.
- It does **not** call `log_request` — the tool doesn't exist on the agent yet, even though the prompt asks for it. Some runs the agent will mention the tool explicitly; that's fine.

> Note the conversation_id shown in the playground URL or panel. We'll be looking for it in Storage and Traces shortly.

## 4. Tour the Functions code and enable `log_request` (5 min)

Open [`../../src/functions/function_app.py`](../../src/functions/function_app.py). The file ships with **every handler commented out** — each lab uncomments the handler(s) it needs. Two things to notice in the scaffolding that's already active:

```python
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
```

- **Python v2 programming model.** Each handler is a decorated Python function on this `app` instance.
- **`AuthLevel.FUNCTION`.** Every endpoint requires a function key. That's why the smoke test fetches the master key with `az functionapp keys list` and why the OpenAPI tool you'll attach in step 6 needs the `x-functions-key` header.

Scan the four `# --- BEGIN … ---` blocks below the scaffolding. Only one matters for this lab — `log_request`. The other three (`persist_assessment`, `notify_reviewer`, `process_reviewer`) plus the `_queue_client()` helper are scoped to Lab 02 and stay commented out for now.

For `log_request`, trace the flow in your head from the commented body: validate JSON → build a governance entry with sensible defaults → upload to `logs/YYYY/MM/DD/<conversation_id>.json` via the lazily-initialised Managed-Identity blob client → return `201` with the blob path. No connection strings — `DefaultAzureCredential` picks up the Function App's Managed Identity (MI) at runtime.

**Now enable it.** In `function_app.py`, find the `# --- BEGIN log_request ---` block and remove the leading `# ` from every code line (keep the four header lines as comments). The result should look like a normal Python function with its `@app.route(...)` decorator. Save the file.

> Sanity check (optional): `python -m py_compile src/functions/function_app.py` from the workshop root verifies the file still parses — no packages needed. The deploy will surface any deeper issue too.

## 5. Deploy the Functions code and smoke-test (10 min)

Deploy the workshop's Python code into the empty Function App:

```bash
azd deploy functions
```

This packages [`src/functions/`](../../src/functions/) (which `azure.yaml` points at), uploads it, and triggers a cold start. Expect ~2–3 min.

> Why a separate deploy and not `azd up`? We provisioned in Lab 00 *without* deploying code so that you could see the empty Function App in step 1. Deploying it now is the moment Functions becomes "real" in this workshop.

When deploy finishes, run the smoke-test script to prove auth + Functions + Managed Identity + Storage + RBAC all work end-to-end:

### PowerShell

```powershell
./labs/01-first-agent/smoke-test.ps1
```

### Bash / Cloud Shell

```bash
chmod +x ./labs/01-first-agent/smoke-test.sh   # first time only
./labs/01-first-agent/smoke-test.sh
```

The script POSTs a synthetic `log_request` and verifies the resulting blob shows up in the `logs` container. It prints `SMOKE TEST PASSED` with the blob path on success. Failures are tagged `FAIL` with a diagnosis line.

## 6. Attach `log_request` as a tool on the agent (13 min)

Now the agent gets the tool the prompt expects.

You need two things:

```bash
azd env get-value AZURE_FUNCTION_APP_HOSTNAME      # e.g. func-noclar-abc.azurewebsites.net
az functionapp keys list --name $(azd env get-value AZURE_FUNCTION_APP_NAME) \
  --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) \
  --query masterKey -o tsv                          # the function key (treat as a secret)
```

In the portal:

1. Open the `noclar-intake` agent → **Tools → + Add → OpenAPI 3.0 specified tool**.
   1.1 in new foundry: tools section → Add → Browse all tools → Custom → OpenAPI tool
2. **Tool name:** `log_request`
3. **Tool description:** `Writes a governance audit log entry to the logs container. MUST be called once at the very start of every conversation, before any substantive question to the user.`
   - The agent uses this description (not the OpenAPI `description` field) to decide *when* to call the tool. Make it specific about the trigger condition.
4. **Schema:** open [`../../src/functions/openapi-intake.json`](../../src/functions/openapi-intake.json), copy the content, paste into the Schema editor.
   - The Foundry portal accepts **JSON only** for OpenAPI specs — not YAML.
   - This spec exposes only `log_request`. Lab 02's orchestrator uses a separate spec ([`openapi-orchestrator.json`](../../src/functions/openapi-orchestrator.json)) so each agent gets exactly the tools it needs.
5. **Edit the `servers[0].url`** — replace `REPLACE-WITH-AZURE_FUNCTION_APP_HOSTNAME` with the hostname you fetched above (just the host, no `https://`).
6. **Authentication:** **API Key**
   - **Auth type:** `header`
   - **Header name:** `x-functions-key`
   - **API key value:** paste the function key from `az functionapp keys list`.
   6.1 For new portal:
      - Authentication: Connection → Add a new connection
      - Key: x-functions-key
      - Value: paste the function key from `az functionapp keys list`.
7. **Create**.

You should now see one tool on the agent: `log_request`.
(feel free to delete the web search tool)

## 7. Re-test in the Playground (5 min)

Open a **new conversation** in the playground (so the trace is clean), send the same intake opener as in step 3, and watch the agent call `log_request` first.

You should see:

- A tool-call card for `log_request` in the conversation pane, with a `201` response containing `log_blob`.
- Only then the agent greeting + first structured intake question.

Optional sanity check from the CLI:

```bash
storage=$(azd env get-value AZURE_STORAGE_ACCOUNT)
az storage blob list --account-name "$storage" --container-name logs \
  --auth-mode login --query "[].name" -o tsv
```

You should see one new blob per playground conversation since the smoke test.

## 8. Open Traces (5 min)

In the portal: **Tracing → Recent runs → click the run from step 7**.

You should see:

- A top-level span for the user message.
- A child span for the `log_request` tool call (with HTTP status + duration).
- An LLM span with model + token counts.

> Take 2 minutes to expand the spans. Traces are the single most important debugging tool you have for the rest of the workshop.

## 9. Trigger a guardrail (2 min)

Send the agent a clearly inappropriate prompt (e.g. an obviously harassing message). The default content-safety filter should block it. Confirm the block appears in Traces as a `content_filter` event.

## ✅ Done when

- [ ] Agent `noclar-intake` exists in the Foundry portal with one tool: `log_request`.
- [ ] `azd deploy functions` succeeded and `./labs/01-first-agent/smoke-test.ps1` (or `.sh`) printed `SMOKE TEST PASSED`.
- [ ] A playground run shows a `log_request` tool call returning a `log_blob` path.
- [ ] You can show a Trace with the tool-call span expanded.
- [ ] At least one content-safety block is visible in Traces.

## Discussion (5 min wrap-up)

- Where would `log_request` be insufficient as a governance log? (Hint: voice channel handoff, retries, agent-to-agent calls.)
- What metadata would your firm want in the log that the current schema does not capture?
- Compare: the agent worked *without* the tool in step 3 (just ignoring its own prompt rule). What does that tell you about how strictly LLMs follow instructions, and what's the right control point?

## Reference

- Prompt: [`src/agents/prompts/intake.md`](../../src/agents/prompts/intake.md)
- Function source: [`src/functions/function_app.py`](../../src/functions/function_app.py) → `log_request`
- Tool schema: [`src/functions/openapi-intake.json`](../../src/functions/openapi-intake.json)
