# Lab 03 — Document Understanding & Knowledge Grounding

**Duration:** 60 minutes (Block 3)
**Outcome:** The sample-document corpus is indexed in Azure AI Search
using a **hybrid retrieval** schema (vector + keyword + filterable
metadata), a new `noclar-grounded` agent answers cited questions
against that index, and Azure AI **Content Understanding** extracts a
small structured schema from a contract — feeding back into the Lab 02
intake flow.

---

## What is happening and why

The corpus is small (~6 documents, ~20–30 chunks). On that volume
**pure vector** retrieval is noisy. You'll build a **hybrid** index
where each chunk carries:

| Field | Type | Why |
|---|---|---|
| `id` | string (key) | `<document_id>-<chunk_idx>` |
| `document_id` | string, filterable | join back to source |
| `title` | searchable | shown in citations |
| `document_type` | filterable + facetable | `policy` / `regulation` / `contract` / `ledger` / `witness-statement` |
| `language` | filterable | `en` / `de` |
| `jurisdiction` | filterable | `HR` / `BiH` / `DE` / `EU` / `global` |
| `effective_date` | DateTimeOffset, filterable + sortable | for date-range queries |
| `chunk_text` | searchable (BM25) | keyword side of the hybrid |
| `chunk_vector` | Collection(Single), 1536 dims | vector side |

Queries combine all three:

1. **Vector search** on `chunk_vector` (embedded with
   `text-embedding-3-small`),
2. **Keyword search** on `chunk_text` (BM25, fused via RRF),
3. **`$filter`** on the structured fields (e.g.
   `document_type eq 'policy' and language eq 'en'`).

---

## 1. Uncomment the per-lab files (5 min)

| File | Purpose |
|---|---|
| `src/agents/lab03/ingest_corpus.py` | Build the index + upload chunks. |
| `src/agents/lab03/ground_query.py` | Hybrid query CLI. |

```bash
python -m py_compile src/agents/lab03/*.py
pip install -r src/agents/lab03/requirements.txt
```

YAML front-matter on every doc under `data/sample-docs/` is already
in place (the workshop ships it). Skim one:

```bash
head -n 10 data/sample-docs/internal-policy-anti-bribery.md
```

## 2. Build the index and ingest (5 min)

```bash
python -m src.agents.lab03.ingest_corpus
```

Expected output: `Indexed N chunks across 6 documents`.

In the portal: **Connections → Search → Indexes → `noclar-corpus`**
exists, with the schema above and the chunks visible under **Search
Explorer**.

## 3. Feel the difference in Search Explorer (5 min)

Run these three queries in **Search Explorer**:

| Query | What it tests |
|---|---|
| `search=*&$count=true` | total chunk count |
| `search=success fee&queryType=simple` | keyword-only top-k |
| `search=success fee&$filter=document_type eq 'contract'` | same query, contract docs only |

Note how filters narrow the candidate set *before* ranking.

## 4. Create the grounded agent in the portal (10 min)

**Build → Agents → + New agent**:

- **Name:** `noclar-grounded`
- **Model:** `gpt-4.1-mini`
- **Instructions:** paste
  [`src/agents/prompts/grounded.md`](../../src/agents/prompts/grounded.md).
  Note the explicit rules to (i) extract filter hints from the
  user's phrasing, (ii) issue a hybrid query, (iii) cite every
  factual claim by `document_id`.
- **Knowledge → Azure AI Search:** connect the search service, pick
  the `noclar-corpus` index, **enable hybrid retrieval** (the toggle
  is labelled "use vector + text" on newer portal builds, or sits
  inside the File Search / Search index tool config on older ones).
- **Save.**

## 5. Test grounded retrieval (10 min)

Run these three in the **Playground**:

| Question | Expected behaviour |
|---|---|
| *"What requirements does the anti-bribery policy impose on consultancy contracts above EUR 100,000?"* | Cited answer pointing to `internal-policy-anti-bribery`. |
| *"What does the regulatory guidance say about reporting suspected NOCLAR matters?"* | Citation from a `document_type='regulation'` doc — IDW PS 210 or ISA 250 — **not** from the policy or the contract. |
| *"How large were the bonus payments to the management board in 2024?"* | Agent declines: "I cannot find any evidence for this in the index." |

Now run the same three through the CLI so you can see the filter
applied explicitly:

```bash
python -m src.agents.lab03.ground_query \
  "What requirements does the anti-bribery policy impose..." \
  --document-type policy

python -m src.agents.lab03.ground_query \
  "What does the regulatory guidance say about reporting..." \
  --document-type regulation

python -m src.agents.lab03.ground_query \
  "How large were the bonus payments to the management board?"
```

The CLI prints the hybrid top-k *and* the agent's cited answer.

## 6. Run Content Understanding on a contract (10 min)

In the portal: **Content Understanding → New analyzer → From
scratch**:

- **Name:** `consultancy-contract`
- **Schema** (~5 fields):
  - `parties` — string
  - `effective_date` — date
  - `total_value_eur` — number
  - `success_fee_percent` — number
  - `deliverable_required_before_payment` — string
  - `governing_law` — string
- **Upload:** `data/sample-docs/contract-excerpt-consultancy.md`
- **Run analysis.** Inspect the structured JSON output.

## 7. Compare RAG vs extraction (5 min)

Ask the grounded agent: *"Which success-fee clause applies?"* —
expect prose + `[contract-excerpt-consultancy]` citation.

Look at the Content Understanding output — expect
`success_fee_percent: 4`.

> **When do you want which?** Prose with citations preserves
> context; the structured field is what a downstream system can
> *act* on. In production, you usually want both: extraction for the
> deterministic field that drives a workflow, RAG for the
> human-readable narrative around it.

## 8. Feed the extract back into Lab 02 (5 min)

Copy the Content Understanding JSON into a Python dict and append
it to `IntakeFacts.documented_facts` before calling the drafter.
Sketch:

```python
intake_facts.documented_facts.append({
    "source": "contract-excerpt-consultancy",
    "extracted_by": "content-understanding/consultancy-contract",
    "fields": cu_output,
})
```

This is how the workflow grows beyond what the participant types:
deterministic extraction fills in fields, RAG fills in context, the
human still approves.

---

## ✅ Done when

- [ ] `noclar-corpus` index exists with N chunks across the 6
      sample docs.
- [ ] `noclar-grounded` agent exists with the corpus connected and
      hybrid retrieval enabled.
- [ ] All three test queries returned the expected behaviour
      (one filtered, one declined).
- [ ] A Content Understanding analyser ran on the contract.
