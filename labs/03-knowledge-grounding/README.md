# Lab 03 — Document Understanding & Knowledge Grounding

**Block 3 · 13:15 – 14:30 (50 min lab)**
**Outcome:** The NOCLAR corpus is indexed in AI Search via Foundry IQ, the grounded agent answers with citations, and Content Understanding extracts structured facts from the same documents.

---

## Why this matters

Two distinct techniques operate on the same evidence:

- **Grounding (RAG):** the agent searches the index and *quotes* what it finds, with citations. Good for "what does the policy say?".
- **Extraction (Content Understanding):** structured fields are pulled out of documents into a schema. Good for "give me the parties, amounts and dates from this contract".

You will use both, and discuss when each is the right tool.

## Pre-conditions

- Lab 00 + Lab 02 done.
- `scripts/seed_foundry_project.py` already populated the index `noclar-corpus`.

## Steps

### 1. Verify the index (5 min)

In the portal: **Connections → noclar-search → Indexes**. You should see `noclar-corpus` with 8 documents indexed.

Quick sanity query in the **Search explorer**:

```
search=*&$filter=language eq 'en'&$count=true
```

Expect all 8 documents to be in English.

### 2. Chat with the grounded agent (10 min)

Open **Agents → noclar-grounded → Test in playground**. Ask:

> What requirements does group policy BR-COM-02 §7 impose on consultancy contracts above EUR 100,000?

You should get an answer with citations to `internal-policy-anti-bribery.md`. Confirm by clicking the citation icon — the relevant passage should be highlighted.

Try a deliberately unanswerable question:

> How large were the bonus payments to the management board in 2024?

The agent must say *"I cannot find any evidence for this in the index."* If it confabulates, raise your hand — that is a prompt-engineering failure.

### 3. Run Content Understanding on a contract (15 min)

In the portal: **Content Understanding → New analyzer → From scratch**.

- Name: `consultancy-contract`
- Schema:
  ```json
  {
    "parties": [{"name": "string", "address": "string", "role": "string"}],
    "effective_date": "string",
    "duration_months": "integer",
    "total_value_eur": "number",
    "success_fee_percent": "number",
    "deliverable_required_before_payment": "boolean",
    "governing_law": "string"
  }
  ```
- Upload `data/sample-docs/contract-excerpt-consultancy.md` and run analysis.

Confirm extracted JSON matches what is in the document.

### 4. Compare grounding vs extraction (10 min)

Ask both the grounded agent and Content Understanding the same question:

> Which success-fee clause applies to the advisory services?

- **Grounded agent:** prose with §3 citation.
- **Content Understanding:** structured field `success_fee_percent: 4`.

Note in your workshop notebook (mental or actual): when do you need the prose, when do you need the structured field?

### 5. Wire the structured extract back into the workflow (10 min)

In a Python notebook or REPL:

```python
import json
from azure.identity import DefaultAzureCredential
# pseudocode — actual Content Understanding SDK call here

extract = {
    "parties": [
        {"name": "Adriatic Advisory d.o.o.", "address": "Split, HR", "role": "consultant"}
    ],
    "total_value_eur": 1200000,
    "success_fee_percent": 4,
    "deliverable_required_before_payment": False,
    "governing_law": "Croatia",
}

# Feed it into the IntakeFacts payload as documented_facts
from src.shared.schemas import IntakeFacts
# extend the intake from Lab 02 with extract fields, re-run orchestrator
```

This is the bridge between *Block 3 (grounding)* and *Block 4 (integration)*: the structured extract is what `persist_assessment` ultimately stores.

## ✅ Done when

- [ ] You have made the grounded agent decline a question for lack of evidence.
- [ ] You have a Content Understanding analyzer that extracts the contract schema.
- [ ] You can articulate when to prefer grounding over extraction.

## Discussion

- Where would the corpus get out of date in a real engagement? How would you trigger re-indexing?
- Foundry IQ today indexes flat text — what about tables in PDFs? How would Content Understanding fit there?
