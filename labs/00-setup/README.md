# Lab 00 — Setup & Verification

**Duration:** 20 minutes (during Welcome block)
**Outcome:** You have an Azure **resource group** with the empty
*shells* of every service used in the workshop, and you can open your
Foundry project in the browser. Lab 00 deploys **no application code**.

---

## What you do here and why

Today's workshop builds a NOCLAR Initial Assessment agent on top of
Azure AI Foundry. To keep the moving parts visible, we **introduce one
service per lab**, and each lab deploys *its own* code:

| Lab | Service introduced | What you build with it |
| --- | --- | --- |
| **00 (here)** | **Azure AI Foundry**, **Application Insights** | Provision empty shells, verify Foundry is reachable. |
| 01 | (no new service) | Create your first agent in the portal. |
| 02 | **Azure Functions**, **Storage queue** | Persist approved memos and notify a reviewer. |
| 03 | **Azure AI Search**, **Content Understanding** | Ingest a small corpus, ground answers with citations. |
| 04 | **MCP**, **Functions-as-tools**, **Voice Live** | Attach Functions and a Learn MCP server as tools; instructor demo of the voice channel. |
| 05 | **Evaluation SDK + portal** | Score the grounded agent two ways. |

To avoid an `azd provision` wait inside every lab, **Lab 00 provisions
all of these resources in one shot** — but **no code, no agents, no
indexes, no connections** are created yet. Every later lab deploys the
code and creates the artefacts it needs.

---

## 0. Permissions you need

You need (or your instructor needs on your behalf):

- **Owner** or **Contributor** on a pre-created Azure resource group
  (`rg-foundry-<initials>`). The Bicep deploys at **resource-group
  scope** — you do **not** need subscription-level rights.
- A `gpt-4.1-mini` model quota assigned to the chosen region
  (**Sweden Central** by default). The instructor confirms this
  before the workshop.
- Optional, for the Lab 04 Voice Live demo: realtime model quota for
  `gpt-realtime-1.5` in the same region. This is **not required** for
  the hands-on labs and is not deployed unless explicitly enabled.
- After provisioning: a handful of data-plane roles on the resources
  inside the RG (Cognitive Services User on Foundry, Storage Blob
  Data Contributor on the storage account, Search Index Data
  Contributor on AI Search, Monitoring Metrics Publisher on App
  Insights). The instructor grants these for you via
  [`scripts/postdeploy-rbac.ps1`](../../scripts/postdeploy-rbac.ps1) /
  [`.sh`](../../scripts/postdeploy-rbac.sh) — see
  [`INSTRUCTOR.md`](./INSTRUCTOR.md).

---

## 1. Pre-flight check

> **About code blocks in these labs.** Code blocks are tagged
> `bash` for syntax highlighting but the commands work
> **identically in PowerShell** (Windows native) — `az`, `azd`,
> `python`, `uv`, `git`. Where the syntax actually differs
> (activating a venv, exporting env vars, line continuations,
> viewing files), the lab shows **both** a bash and a PowerShell
> block side-by-side.

PowerShell (Windows) **or** bash (Codespaces / Linux / macOS):

```bash
az --version
azd version
python --version
git --version
```

> **About `uv`.** Some labs use `uv pip install -r …` because it is
> ~10× faster than `pip`. `uv` requires either a venv or write
> access to the system site-packages — in a devcontainer /
> Codespaces the non-root user has *neither*, so the labs default
> to plain `pip` (which falls back to a user install). If you are
> on Windows native or local Linux/macOS *and* are using a venv,
> swap `pip` for `uv pip` for the speed-up. To install `uv`:
> `pip install uv` or `winget install --id=astral-sh.uv`.

If anything is missing, install the missing CLI before continuing:
[`az`](https://learn.microsoft.com/cli/azure/install-azure-cli),
[`azd`](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd),
[Python 3.11+](https://www.python.org/downloads/), and
[Git](https://git-scm.com/downloads).

## 2. Sign in

```bash
az login
azd auth login
```

If you have more than one subscription:

```bash
az account set --subscription "<YOUR-SUB-NAME-OR-ID>"
```

## 3. Create the resource group (if your instructor hasn't already)

Ask the instructor first — they may have created one for you.

If you are preparing the optional Voice Live demo, first check realtime
model quota in the Azure AI Foundry portal: open the Foundry portal,
go to **Management center → Quotas**, select the workshop region, and
look for `gpt-realtime-1.5`. If quota is available, opt in when you
provision. If quota is not available, leave the flag off; the rest of
the workshop still works.

PowerShell:

```powershell
./scripts/provision-rg.ps1 -ResourceGroup rg-foundry-<initials> -Location swedencentral
# With confirmed realtime quota for the optional voice demo:
./scripts/provision-rg.ps1 -ResourceGroup rg-foundry-<initials> -Location swedencentral -DeployRealtimeModel
```

bash:

```bash
./scripts/provision-rg.sh -g rg-foundry-<initials> -l swedencentral
# With confirmed realtime quota for the optional voice demo:
./scripts/provision-rg.sh -g rg-foundry-<initials> -l swedencentral --deploy-realtime-model
```

The script creates the RG if it does not exist and runs
`azd env new` + `azd env set AZURE_RESOURCE_GROUP=…` + `azd provision`
into it. It also sets `DEPLOY_REALTIME_MODEL` to `true` only when you
pass the realtime flag. It is idempotent.

> **Why a resource group, not a subscription?** You typically don't
> have subscription-owner permissions for a workshop. The Bicep in
> [`infra/main.bicep`](../../infra/main.bicep) targets
> `resourceGroup` scope so an RG-Contributor can deploy it.

## 4. Capture outputs

```bash
azd env get-values > .env
```

Spot-check that at least these keys exist:

- `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT`
- `AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT` (= `gpt-4.1-mini`)
- `AZURE_AI_FOUNDRY_EMBEDDING_DEPLOYMENT` (= `text-embedding-3-small`)
- `AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT` (= `gpt-realtime-1.5`, only
  if you enabled the optional realtime deployment)
- `AZURE_AI_FOUNDRY_PORTAL_URL`
- `APPLICATIONINSIGHTS_CONNECTION_STRING`
- `AZURE_RESOURCE_GROUP`

`.env` is gitignored — never commit it.

## 5. Open your Foundry project

```bash
azd env get-value AZURE_AI_FOUNDRY_PORTAL_URL
```

Open the URL in your browser. Confirm:

- The project `noclar-assessment` is selected (top-left).
- Under **My assets → Models + endpoints** you see two deployments:
  `gpt-4.1-mini` and `text-embedding-3-small`.
  If you enabled the optional realtime deployment, you also see
  `gpt-realtime-1.5`.
- Under **Build → Agents** the list is **empty**.

## 6. (Optional) Peek at Application Insights

In the Azure Portal → your RG → the `appi-…` resource →
**Live Metrics**. The page loads, traffic is zero. You'll come back
here in Lab 02 to watch the orchestration trace happen live.

## ✅ Done when

- [ ] `azd provision` completed against your RG with no errors.
- [ ] `.env` has the six keys listed in step 4.
- [ ] The Foundry portal opens via the deep link; both model
      deployments are visible; the Agents list is empty.

## Fallback

If `azd provision` fails (quota, permissions, network): tell the
instructor your RG name. They will either re-run `provision-rg` with
their own credentials or hand you an `.env` from a pre-provisioned
parallel environment. Skip to step 5 and continue with Lab 01.
