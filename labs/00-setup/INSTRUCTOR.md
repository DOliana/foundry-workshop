# Lab 00 — Instructor notes

These tasks happen **before the workshop** and **once per participant**
in the room. Participants only see [`README.md`](./README.md).

---

## Days before the workshop

1. **Confirm `gpt-5.4-mini` quota** in the workshop region
  (Sweden Central by default). Foundry → your account → Quotas.
  The lab also needs an embeddings model — **`text-embedding-3-small`**
  in the same region. If quota is short, switch region in
  `infra/main.parameters.json` and re-run a dry provision.

  The Lab 04 realtime voice model is optional and not deployed by
  default. Only enable it for instructor/demo environments after
  confirming realtime-model quota:

  ```bash
  azd env set DEPLOY_REALTIME_MODEL true
  ```

### Find deployable model names and versions

Use the Azure CLI model list to confirm which model names and versions
are deployable in a region. The useful fields are nested under `model`,
so query `model.name` / `model.version` rather than top-level `name` /
`version`. This filters to AIServices models with a `GlobalStandard`
deployment SKU and excludes models that are already deprecated or
deprecating:

```powershell
az cognitiveservices model list -l swedencentral --query "sort_by(sort_by([?kind=='AIServices' && model.lifecycleStatus!='Deprecating' && model.lifecycleStatus!='Deprecated' && contains(model.skus[].name, 'GlobalStandard')], &model.name), &model.format)[].{kind:kind,name:model.name,version:model.version,format:model.format,lifecycle:model.lifecycleStatus,skus:model.skus[].name}" -o table
```

```bash
az cognitiveservices model list -l swedencentral --query "sort_by(sort_by([?kind=='AIServices' && model.lifecycleStatus!='Deprecating' && model.lifecycleStatus!='Deprecated' && contains(model.skus[].name, 'GlobalStandard')], &model.name), &model.format)[].{kind:kind,name:model.name,version:model.version,format:model.format,lifecycle:model.lifecycleStatus,skus:model.skus[].name}" -o table
```

For the default deployment, keep [`infra/main.bicep`](../../infra/main.bicep),
[`infra/modules/foundry.bicep`](../../infra/modules/foundry.bicep), and
[`infra/main.parameters.json`](../../infra/main.parameters.json) aligned with
the returned `model.name` and `model.version`. For Sweden Central, the current
workshop default is `gpt-5.4-mini` version `2026-03-17`.

### Required model capabilities

If the default models are unavailable, choose replacements by capability, not
by name alone:

| Workshop use | Required catalog capabilities | Current default |
| --- | --- | --- |
| Hosted Foundry agents, JSON responses, orchestration | `agentsV2=true`, `chatCompletion=true`, `responses=true` | `gpt-5.4-mini` `2026-03-17` |
| Lab 03 vector embeddings | `embeddings=true` | `text-embedding-3-small` `1` |
| Optional Lab 04 Voice Live | `realtime=true`; prefer `gpt-realtime*` names for speech-to-speech | `gpt-realtime-1.5` `2026-02-23` |

Find candidate chat/agent models:

```bash
az cognitiveservices model list -l swedencentral --query "sort_by([?kind=='AIServices' && model.lifecycleStatus!='Deprecating' && model.lifecycleStatus!='Deprecated' && contains(model.skus[].name, 'GlobalStandard') && model.capabilities.agentsV2=='true' && model.capabilities.chatCompletion=='true' && model.capabilities.responses=='true'], &model.name)[].{name:model.name,version:model.version,format:model.format,lifecycle:model.lifecycleStatus,skus:model.skus[].name}" -o table
```

Find candidate embedding models:

```bash
az cognitiveservices model list -l swedencentral --query "sort_by([?kind=='AIServices' && model.lifecycleStatus!='Deprecating' && model.lifecycleStatus!='Deprecated' && contains(model.skus[].name, 'GlobalStandard') && model.capabilities.embeddings=='true'], &model.name)[].{name:model.name,version:model.version,format:model.format,lifecycle:model.lifecycleStatus,skus:model.skus[].name}" -o table
```

Find candidate realtime voice models:

```bash
az cognitiveservices model list -l swedencentral --query "sort_by([?kind=='AIServices' && model.lifecycleStatus!='Deprecating' && model.lifecycleStatus!='Deprecated' && contains(model.skus[].name, 'GlobalStandard') && model.capabilities.realtime=='true' && starts_with(model.name, 'gpt-realtime')], &model.name)[].{name:model.name,version:model.version,format:model.format,lifecycle:model.lifecycleStatus,skus:model.skus[].name}" -o table
```

Quota is exposed separately from catalog capabilities. For OpenAI-format models,
quota rows commonly use `OpenAI.GlobalStandard.<model-name>` even when the
deployment account kind is `AIServices`:

```bash
az cognitiveservices usage list -l swedencentral --query "sort_by([?starts_with(name.value, 'OpenAI.GlobalStandard.') || starts_with(name.value, 'AIServices.GlobalStandard.')], &name.value)[].{name:name.value,current:currentValue,limit:limit,unit:unit}" -o table
```

1. **Pre-create one resource group per participant** if you want to
   avoid the in-room RG-create step:

   ```powershell
   foreach ($initials in @("ab","cd","ef")) {
     ./scripts/provision-rg.ps1 -ResourceGroup "rg-foundry-$initials" -Location swedencentral
   }
   ```

   ```bash
   for initials in ab cd ef; do
     ./scripts/provision-rg.sh -g "rg-foundry-$initials" -l swedencentral
   done
   ```

   This creates the RG, runs `azd provision`, and leaves a working
   `.env` next to each azd environment. ~10 min per RG; parallelise
   on the CLI if you have many.

2. **Smoke-test one provisioned RG end-to-end** (you, not the participant): open the Foundry portal, confirm the chat and embedding model deployments, eyeball the empty Functions app, peek at Live Metrics. If you enabled `DEPLOY_REALTIME_MODEL`, confirm the realtime deployment too. If anything is off, fix it once now rather than 15 times in the room.

## In the room — once per participant

If you are the one running `azd provision` (you own the RG), you can
just self-assign the roles — no UPN needed:

```powershell
./scripts/postdeploy-rbac.ps1 -ResourceGroup rg-foundry-ab
```

```bash
./scripts/postdeploy-rbac.sh --rg rg-foundry-ab
```

When you provision on behalf of someone else, pass their UPN or AAD
object id:

```powershell
./scripts/postdeploy-rbac.ps1 -ResourceGroup rg-foundry-ab -Principals user@contoso.com
```

```bash
./scripts/postdeploy-rbac.sh --rg rg-foundry-ab --principal user@contoso.com
```

The script assigns every RG-scoped data-plane role the participant
needs:

- **Cognitive Services User** on the Foundry account (run agents,
  call models)
- **Storage Blob Data Contributor** on the storage account (read /
  write blobs from Functions and Python)
- **Storage Queue Data Contributor** on the storage account
  (enqueue / dequeue reviewer messages)
- **Search Index Data Contributor** on the AI Search service (Lab 03
  ingest)
- **Monitoring Metrics Publisher** on App Insights (custom metrics
  from the orchestrator)

The script is idempotent — safe to re-run if you forgot a role.

## Subscription-level prerequisites (cannot be done by an RG-Contributor)

These have to be in place before the workshop starts, by someone with
the relevant subscription rights:

- **Model quota assignment** for `gpt-5.4-mini`,
  `text-embedding-3-small`, and `gpt-realtime-1.5` (or
  whichever realtime model your region carries) in the workshop
  region.
  If `azd provision` fails with `DeploymentModelNotSupported`, check
  the region's available model list and make sure the Bicep uses both
  the supported model name and version.
- **Resource providers** registered:
  `Microsoft.CognitiveServices`, `Microsoft.Search`,
  `Microsoft.Insights`, `Microsoft.OperationalInsights`,
  `Microsoft.Storage`, `Microsoft.Web`.
- (Optional, Lab 04 voice demo) Voice Live regional reachability
  confirmed from the demo machine per the
  [Lab 04 instructor notes](../04-integration-voice/INSTRUCTOR.md).
  No ACS resource is provisioned — the voice demo is internet-only.

## During Lab 00

Stand at the back of the room. The instructor's only in-room job in
Lab 00 is running `postdeploy-rbac` per participant once they tell
you their RG name + UPN.
