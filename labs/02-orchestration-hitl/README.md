# Lab 02 — Multi-Agent Orchestration & Human-in-the-Loop

**Block 2 · 11:00 – 12:15 (50 min lab)**
**Outcome:** Run the NOCLAR orchestrator end-to-end and observe both HITL checkpoints.

---

## Why this matters

The Initial Assessment Memo is **never produced unsupervised**. Two explicit human approvals are designed into the workflow:

1. **HITL #1 — confirm the legal classification** before drafting the memo.
2. **HITL #2 — approve the drafted memo** before it is persisted.

Persistence is enforced at *two* layers: the orchestrator checks, AND the `persist_assessment` Function refuses memos without `approved_by`. This is defense in depth.

## Pre-conditions

- Lab 00 done (agents seeded).
- Pre-installed Python deps from Lab 00 (`src/agents/requirements.txt`).

## Steps

### 1. Read the orchestrator (10 min)

Open `src/agents/orchestrator.py` and walk through `run_workflow`. Focus on:

- The order of specialist calls (`grounded` → `classifier` → `drafter`).
- Where `approve_classification` and `approve_memo` are invoked.
- How `memo.approved_by` is set right before `persist_assessment`.

### 2. Prepare a fake `IntakeFacts` payload (5 min)

Create `labs/02-orchestration-hitl/run_helios.py`:

```python
from src.agents.orchestrator import run_workflow
from src.shared.schemas import IntakeFacts, Person, SourceReference

intake = IntakeFacts(
    case_id="BPW-2025-HEL-001",
    client_name="Helios Industrieanlagen GmbH",
    engagement_id="BPW-2025-HEL-001",
    summary=(
        "Anonymous tip and internal whistleblower raise initial suspicion of "
        "improper advisor payments (EUR 740k) to Adriatic Advisory d.o.o. "
        "with temporal proximity to three public-sector contracts in HR/BiH."
    ),
    triggering_event="Anonymous email to the Audit Committee 2026-02-14 plus internal report from Schneider 2026-02-19",
    persons=[
        Person(name="K. Petrović", role="Regional Sales Director SEE", organization="Helios", relevance="Sole approver of all invoices"),
        Person(name="A. Berger", role="Procurement Lead SEE", organization="Helios", relevance="Was not involved in the engagement"),
        Person(name="M. Schneider", role="Deputy Head of Internal Audit", organization="Helios", relevance="Internal whistleblower"),
    ],
    documented_facts=[
        "9 invoices totalling EUR 740,000 between 11/2024 and 12/2025",
        "Success fees temporally linked to public-sector contracts worth more than EUR 11 million",
        "All invoices lack the second signature required by group policy BR-COM-02 §7",
    ],
    unconfirmed_claims=[
        "Personal connection between Petrović and Marić (Adriatic CEO)",
    ],
    sources=[
        SourceReference(document_id="intake-email-01-anonymous-tip.md"),
        SourceReference(document_id="intake-email-02-internal-whistleblower.md"),
        SourceReference(document_id="payment-ledger-extract.md"),
        SourceReference(document_id="witness-statement-procurement-lead.md"),
    ],
)

result = run_workflow(intake, user_principal="mara.lehmann@example.com")
print(result)
```

### 3. Run it (15 min)

```bash
python -m labs.02-orchestration-hitl.run_helios
```

What you should see:

- Console prints with both HITL prompts.
- At HITL #1, type **n** to reject — observe how the workflow stops. Re-run and approve.
- At HITL #2, approve.
- A `memo_blob` path is printed at the end.

### 4. Inspect the persisted memo (5 min)

```powershell
$account = (azd env get-value AZURE_STORAGE_ACCOUNT).Trim()
$blob = "<memo_blob from output>"
az storage blob download --account-name $account --container-name assessments --name $blob --file ./memo.json --auth-mode login
code ./memo.json
```

Compare to `data/memo-template/example-helios.md`.

### 5. Try the negative path (10 min)

Modify `run_helios.py` to remove `approved_by` from the memo and call `persist_assessment` directly:

```python
from src.agents.tools.functions_tools import persist_assessment
persist_assessment({"case_id": "test", "approved_by": None, ...})
```

You should get HTTP 409 *"memo missing approved_by — HITL gate not satisfied"*. **The Function enforces the gate.**

### 6. Open Traces (5 min)

Open the App Insights *Application Map*. You should see calls to:

- `noclar-orchestrator` (root)
- `noclar-grounded`, `noclar-legal-classifier`, `noclar-drafter` (children)
- The HTTP-triggered Functions (`persist_assessment`, `notify_reviewer`)

## ✅ Done when

- [ ] You ran the workflow end-to-end and have a persisted memo blob.
- [ ] You have rejected at one HITL gate at least once.
- [ ] You have seen `persist_assessment` refuse an unapproved memo.

## Discussion

- Where should the HITL UI live in production — Teams adaptive card? web app? Outlook approval? Why?
- Could the orchestrator be replaced with Foundry Workflows declarative workflows? Where would the trade-offs be?
