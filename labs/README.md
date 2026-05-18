# Workshop labs — outline & artefacts

Living index of what each lab does, what it produces **on your laptop**, and what it produces **in Azure**. Tick off the rows as you complete each lab so you can see the system grow.

This is a tracker, not a tutorial — follow each lab's own `README.md` for the actual steps.

---

## Lab 00 — Setup & Verification

**Goal:** A complete resource group with the empty *shells* of every service used in the workshop, plus a working browser session against your own Foundry project.

**What happens:**

1. Sign in with `az login` + `azd auth login`.
2. `azd env new foundry-<initials>` creates an azd environment locally.
3. `azd provision` (not `azd up`) executes the Bicep at [`infra/main.bicep`](../infra/main.bicep) against your subscription. **Infra only — no Function code is deployed yet.**
4. `azd env get-values > .env` snapshots the outputs into a local file.
5. Open the Foundry portal via the deep link in `AZURE_AI_FOUNDRY_PORTAL_URL` and confirm the project + `o4-mini` deployment are visible.
6. (Optional) Peek at App Insights Live Metrics.

### Created locally

| Artefact | Path | Notes |
| --- | --- | --- |
| azd environment | `.azure/foundry-<initials>/` | Environment name, location, outputs cache. Gitignored. |
| `.env` | `foundry-workshop/.env` | Snapshot of `azd env get-values`. Gitignored. Used by Python scripts in later labs. |

### Created in Azure

All resources land in the resource group `rg-foundry-<initials>` (whatever you used as the env name). After Lab 00 they are *empty platforms* — populated in later labs.

| Resource | Service | State after Lab 00 |
| --- | --- | --- |
| `aif-<suffix>` | Azure AI Foundry account (AIServices) | Active; `o4-mini` model deployment ready. **Used in Lab 00.** |
| `aif-<suffix>/noclar-assessment` | Foundry project | Active; **no agents, no connections.** Used from Lab 01 onwards. |
| `appi-<suffix>` | Application Insights | Receiving zero traffic. **Used in Lab 00 (Live Metrics peek).** |
| `log-<suffix>` | Log Analytics workspace | Backing store for App Insights. |
| `func-<suffix>` | Azure Functions (Flex Consumption) | App exists; **no code deployed**. Used from Lab 01. |
| `stg<suffix>` | Storage account | Containers `sample-docs`, `assessments`, `logs`, `deploymentpackage` exist (empty). Queue `reviewer-inbox` exists (empty). |
| `srch-<suffix>` | Azure AI Search (Basic) | Service running; **no index**. Used in Lab 03. |
| `acs-<suffix>` | Azure Communication Services | Provisioned; **no phone number, no events**. Used in Lab 04 (voice). |

### Key env vars exported

Only these are actively used during Lab 00. The rest become relevant from Lab 01 onwards.

- `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT`
- `AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT`
- `AZURE_AI_FOUNDRY_PORTAL_URL`
- `APPLICATIONINSIGHTS_CONNECTION_STRING`

### Done when

- [ ] Resource group `rg-foundry-<initials>` shows ~8 resources in the Azure Portal.
- [ ] `.env` exists and contains the four keys above.
- [ ] Foundry portal opens via the deep link; `o4-mini` is listed under **Models + endpoints**; **Agents** list is empty.

---

## Lab 01 — Your First Agent + Functions as Tools

**Goal:** A `noclar-intake` agent you created by hand in the Foundry portal, talking to a `log_request` Azure Function tool you deployed yourself, with the round-trip visible in Traces.

**What happens:**

1. Open the Foundry project (using `AZURE_AI_FOUNDRY_PORTAL_URL` from Lab 00).
2. Create the `noclar-intake` agent in the portal: model `o4-mini`, system prompt pasted from [`../src/agents/prompts/intake.md`](../src/agents/prompts/intake.md), no tools yet.
3. Test it in the Playground — observe a German intake conversation without `log_request`.
4. Deploy the Functions code with `azd deploy functions` and run the smoke test ([`01-first-agent/smoke-test.ps1`](./01-first-agent/smoke-test.ps1) / [`.sh`](./01-first-agent/smoke-test.sh)) to confirm the round-trip.
5. Attach `log_request` as an OpenAPI tool on the agent (using [`../src/functions/openapi.yaml`](../src/functions/openapi.yaml) + the function key from `az functionapp keys list`).
6. Re-test in the Playground — observe the tool call.
7. Open Traces and inspect the run.
8. Trigger a content-safety guardrail.

### Created locally

| Artefact | Path | Notes |
| --- | --- | --- |
| (none new) | — | All edits in this lab happen in the Foundry portal. The repo files referenced (prompt, OpenAPI spec) already exist. |

### Created in Azure

| Resource | Service | State after Lab 01 |
| --- | --- | --- |
| `func-<suffix>` | Functions app | **Code deployed** (4 functions live: `log_request`, `persist_assessment`, `notify_reviewer`, `process_reviewer`). Only `log_request` is exercised in this lab. |
| `stg<suffix>/logs` | Storage blob container | First log blobs appear (one per smoke-test call + one per playground conversation). |
| `aif-<suffix>/noclar-assessment` | Foundry project | Now contains **1 agent**: `noclar-intake` with one tool (`log_request` via OpenAPI). Traces start populating. |
| `appi-<suffix>` | Application Insights | Receiving traces from Foundry agent runs + Functions invocations. |

### Key env vars used

- `AZURE_AI_FOUNDRY_PORTAL_URL` (open portal)
- `AZURE_FUNCTION_APP_NAME`, `AZURE_RESOURCE_GROUP` (get function key, run smoke test)
- `AZURE_FUNCTION_APP_HOSTNAME` (paste into OpenAPI spec `servers:` block)
- `AZURE_STORAGE_ACCOUNT` (optional CLI sanity check on log blobs)

### Done when

- [ ] Agent `noclar-intake` exists in the Foundry portal with one tool: `log_request`.
- [ ] Smoke test printed `SMOKE TEST PASSED`.
- [ ] A playground conversation shows a `log_request` tool call returning a `log_blob`.
- [ ] You can show a Trace with the tool-call span expanded.
- [ ] A content-safety block is visible in Traces.

---

## Lab 02 — *(to be added)*

## Lab 03 — *(to be added)*

## Lab 04 — *(to be added)*

## Lab 05 — *(to be added)*
