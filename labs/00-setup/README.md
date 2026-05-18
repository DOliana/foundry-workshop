# Lab 00 — Setup & Verification

**Duration:** 20 minutes (during Welcome block)  
**Outcome:** You have an Azure resource group with the empty *shells* of every service used in the workshop, and you can open your Foundry project in the browser.

---

## What you do here and why

Today's workshop builds a NOCLAR Initial Assessment agent on top of Azure AI Foundry. To keep the moving parts visible, we **introduce one service per lab**:

| Lab | Service introduced | What you build with it |
| --- | --- | --- |
| **00 (here)** | **Azure AI Foundry**, **Application Insights** | Provision everything, then verify Foundry is reachable. |
| 01 | **Azure Functions** | Deploy a `log_request` Function and call it from your first agent as a tool. |
| 02 | **Storage queue** | Use the queue + a queue-triggered Function for the human-in-the-loop callback. |
| 03 | **Azure AI Search** | Create an index and ground the agent on the NOCLAR corpus. |
| 04 | **MCP** (Microsoft Learn server) | Attach an MCP tool to the orchestrator. |
| 05 | **Evaluation SDK** | Score agent runs offline. |

To avoid an extra `azd provision` wait inside every lab, **Lab 00 provisions all of these resources in one shot** — but no application code is deployed yet. Every lab that introduces a new service is the lab where you also deploy the code or configuration that brings that service to life. Lab 00 itself only uses Foundry and App Insights; the other resources sit dormant in the resource group until their lab.

You also **do not create any agents, indexes or connections** in Lab 00. Those are created in the labs where they're first used.

---

## 1. Pre-flight check

```bash
az --version
azd version
python --version
git --version
```

All four must succeed. If anything is missing, see [`../../PARTICIPANT-SETUP.md`](../../PARTICIPANT-SETUP.md).

## 2. Sign in

```bash
az login
az account show --query "{sub: id, name: name, tenant: tenantId}" -o table
azd auth login
```

If you have multiple subscriptions:

```bash
az account set --subscription "<YOUR-SUB-NAME-OR-ID>"
```

## 3. Clone & provision

```bash
git clone <REPO-URL> foundry-workshop
azd env new foundry-<initials>
azd env set AZURE_LOCATION swedencentral
azd provision
```

When prompted:

> **Why `azd provision` and not `azd up`?** `azd up` would also deploy the Functions code immediately. We want the Functions app to start out **empty** — you will deploy code into it in Lab 01, so you can see the before/after. `azd provision` creates only the infrastructure shells.

> **Why `AZURE_LOCATION` is set explicitly:** `azd` does not prompt for location once an environment exists, and the subscription-scoped Bicep deployment fails with `The 'location' property must be specified` if it's missing. Use `swedencentral` (where we have model quota) unless the instructor tells you otherwise.

Provisioning takes ~10 minutes. While it runs, skim [`../../README.md`](../../README.md) for the workshop overview.

After it finishes you should see a Foundry account, a Foundry project (`noclar-assessment`) with an `o4-mini` deployment, an empty Function App, a Storage account, an AI Search service, an Application Insights workspace, and an Azure Communication Services resource. Empty here means: the platforms exist, but no agents, no Function code, no Search indexes, no queue messages.

## 4. Capture outputs

```bash
azd env get-values > .env
```

This writes resource endpoints and names into a local `.env` file used by Python scripts later in the workshop. **Never commit this file** — it is already in `.gitignore`.

Spot-check that at least these keys exist:

- `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT`
- `AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT` (= `o4-mini`)
- `AZURE_AI_FOUNDRY_PORTAL_URL`
- `APPLICATIONINSIGHTS_CONNECTION_STRING`

The rest (`AZURE_FUNCTION_APP_*`, `AZURE_AI_SEARCH_*`, `AZURE_STORAGE_*`) will matter from Lab 01 onwards.

## 5. Open your Foundry project

Get the deep link (use command below or check `.env` file):

```bash
azd env get-value AZURE_AI_FOUNDRY_PORTAL_URL
```

Open the URL in the browser. Confirm:

- The project `noclar-assessment` is selected (top-left).
- Under **My assets → Models + endpoints** you see `o4-mini`.
- Under **Build → Agents** the list is **empty** (you'll create agents starting in Lab 01).

> If `AZURE_AI_FOUNDRY_PORTAL_URL` is empty, you provisioned against an older
> version of the infra. Re-run `azd provision` to refresh the outputs, or build
> the URL by hand from `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`,
> `AZURE_AI_FOUNDRY_NAME` and `AZURE_AI_FOUNDRY_PROJECT_NAME`.

## 6. (Optional) Peek at Application Insights

App Insights is the single observability pane for both your Functions calls and your Foundry agent runs. We won't query traces in Lab 00 — there's nothing running yet — but it's worth opening the resource once so you know where to find it later.

In the [Azure Portal](https://portal.azure.com), navigate to your resource group → the Application Insights resource (named `appi-…`) → **Live Metrics**. The page should load and show idle/zero traffic. You'll come back here in Lab 02 to watch the orchestration trace happen in real time.

## ✅ Done when

- [ ] `azd provision` completed without errors.
- [ ] `.env` has `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT`, `AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT`, `AZURE_AI_FOUNDRY_PORTAL_URL`, `APPLICATIONINSIGHTS_CONNECTION_STRING`.
- [ ] The Foundry portal opens via the deep link, the project `noclar-assessment` is selected, and `o4-mini` shows under **Models + endpoints**.
- [ ] The Foundry **Agents** list is empty (it will be populated as you work through Labs 01–04).

## Fallback

If `azd provision` fails (quota, permissions, network), tell the instructor your azd env name. The instructor has pre-provisioned environments ready and will hand you an `.env` file you can drop into your local clone. From there, skip to step 5 and continue with Lab 01.
