# Lab 05 — Evaluation, Governance & Production Readiness

**Block 5 · 16:00 – 16:45 (mostly discussion + cherry-picked notebook)**
**Outcome:** You can describe how to evaluate the NOCLAR agent against the supplied datasets and what the production hardening checklist looks like.

---

## Walking through the day's telemetry (10 min)

Open **Application Insights → Application Map**. You should see all five blocks represented:

- Block 1: a single span chain per playground run.
- Block 2: deeper call trees with multiple specialist agents.
- Block 3: agent → Search → agent.
- Block 4: agent → Function → queue → Function.

Discussion:

- Where would you have wanted **more** information in the spans?
- What is the right cardinality for custom dimensions? (case_id yes, conversation_id yes, message_text no.)

## Running an eval (15 min)

```bash
pip install azure-ai-evaluation
```

```python
# labs/05-evaluation/run_eval.py (sketch)
import json
from pathlib import Path
from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator

# Load the dataset
items = [json.loads(line) for line in Path("data/eval/grounding-citations.jsonl").read_text().splitlines()]

# Wire the evaluator
groundedness = GroundednessEvaluator(model_config={
    "azure_endpoint": "<foundry endpoint>",
    "azure_deployment": "<gpt-4.1-mini deployment>",
})

# Run against the grounded agent
results = []
for item in items:
    # 1. Ask the grounded agent the query
    # 2. Score with the evaluator
    ...

print(json.dumps(results, indent=2))
```

> A complete runnable version is provided as a stretch goal in `labs/05-evaluation/run_eval.py` (see the comments inside).

## Production hardening checklist (15 min discussion)

| Area | Workshop posture | Production posture |
|---|---|---|
| Identity | DefaultAzureCredential | Workload identity / federated cred only |
| Network | Public endpoints | Private endpoints, no public access |
| Secrets | App settings | Key Vault references + APIM in front of Functions |
| Logging | App Insights only | + SIEM forwarding for governance log |
| HITL UI | Console prompt | Teams adaptive card or web app, audit-logged |
| Memo storage | Blob | Blob + immutability policy + WORM retention |
| Voice telephony | Browser mic demo | ACS phone number + EventGrid + callback URL |
| Eval | Manual jsonl | Scheduled CI eval against frozen datasets |
| Knowledge base | One-off seed | Scheduled indexer + change-data-capture |

## Tying it back to the NOCLAR process

The whole day produces *one* artefact that matters to the audit firm: the Initial Assessment Memo, with an audit-trail.

- Every intake conversation has a `log_request` entry (governance).
- Every memo has a HITL approval recorded (Section 10 of the template, `approved_by` + `approved_at` field on the persisted blob).
- Every claim in the memo is traceable to a source (Section 3 / `sources`).
- Every classification has a confidence (`LegalNormReference.confidence`).
- Every eval run has a score against a frozen dataset.

This is the minimum viable governance posture; you'd extend it for your firm's specific risk appetite.

## ✅ Done when

- [ ] You have run at least one eval row by hand.
- [ ] You can list three production hardening items not done in the workshop.
- [ ] You can describe the audit trail end-to-end.

## What we did NOT do (intentionally)

- Foundry Workflows (declarative): we used code orchestration. Discuss when declarative is preferable.
- Phone-call telephony with ACS: needs procurement lead time; replaced by browser mic demo.
- Fine-tuning / distillation: out of scope for a 1-day workshop.
