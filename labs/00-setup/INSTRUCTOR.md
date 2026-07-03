# Lab 00 — Instructor notes

These tasks happen **before the workshop** and **once per participant**
in the room. Participants only see [`README.md`](./README.md).

---

## Days before the workshop

1. **Confirm `gpt-4.1-mini` quota** in the workshop region
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

2. **Pre-create one resource group per participant** if you want to
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

3. **Smoke-test one provisioned RG end-to-end** (you, not the participant): open the Foundry portal, confirm the chat and embedding model deployments, eyeball the empty Functions app, peek at Live Metrics. If you enabled `DEPLOY_REALTIME_MODEL`, confirm the realtime deployment too. If anything is off, fix it once now rather than 15 times in the room.

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

- **Model quota assignment** for `gpt-4.1-mini`,
  `text-embedding-3-small`, and `gpt-realtime-1.5` (or
  whichever realtime model your region carries) in the workshop
  region.
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
