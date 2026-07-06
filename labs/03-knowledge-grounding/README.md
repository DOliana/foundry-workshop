# Lab 03 — Document Understanding & Knowledge Grounding

**Duration:** 60 minutes (Block 3)
**Outcome:** The sample-document corpus is indexed in Azure AI Search
using a **hybrid retrieval** schema (vector + keyword + semantic
re-ranker + filterable metadata), a new `noclar-grounded` agent
answers cited questions against that index, and Azure AI **Content
Understanding** extracts a small structured schema from a contract —
feeding back into the Lab 02 intake flow.

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
| `chunk_text` | searchable (BM25, also used by the semantic re-ranker) | keyword side of the hybrid |
| `chunk_vector` | Collection(Single), 1536 dims, profile = `default` (vectorizer = `default-openai`) | vector side |

Queries combine four signals:

1. **Vector search** on `chunk_vector` (embedded with
   `text-embedding-3-small`),
2. **Keyword search** on `chunk_text` (BM25, fused with the vector
   ranking via RRF),
3. **`$filter`** on the structured fields (e.g.
   `document_type eq 'policy' and language eq 'en'`),
4. **Semantic re-ranker** (Microsoft's L2 model) over the top ~50
   fused hits, which is what makes natural-language questions over
   policy/regulatory prose return the right chunk first.

The index is created with a `default` semantic configuration (title
field = `title`, content field = `chunk_text`) and the vector profile
references an `AzureOpenAIVectorizer` so Foundry can embed the user's
query at search time. Without the vectorizer Foundry's knowledge
picker only exposes Simple + Semantic; without the semantic config
the picker hides the Hybrid + semantic option.

---

## 1. Uncomment the per-lab files (5 min)

| File | Purpose |
|---|---|
| `src/labs/lab03/ingest_corpus.py` | Build the index + upload chunks. |
| `src/labs/lab03/ground_query.py` | Hybrid query CLI. |

```bash
python -m py_compile src/labs/lab03/*.py
pip install -r src/labs/lab03/requirements.txt
```

YAML front-matter on every doc under `data/sample-docs/` is already
in place (the workshop ships it). Skim one:

bash:

```bash
head -n 10 data/sample-docs/internal-policy-anti-bribery.md
```

PowerShell:

```powershell
Get-Content data/sample-docs/internal-policy-anti-bribery.md -TotalCount 10
```

## 2. Build the index and ingest (5 min)

```bash
python -m src.labs.lab03.ingest_corpus
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

### 4a. (One-time) Connect AI Search to the project

`azd provision` deploys the AI Search service and grants the project's
managed identity `Search Index Data Contributor` on it, but it does
**not** pre-create the Foundry → Search *connection* (that resource
type is still preview-only in bicep). You create it once, in the
portal:

1. **Management center → Connected resources → + New connection →
   Azure AI Search.**
2. **Subscription / Resource group / Service:** pick the search
   service deployed in your RG (`srch-<token>`).
3. **Authentication:** pick **API key**. Foundry pulls the search
   service admin key for you — no copy/paste needed.
   "Microsoft Entra ID — project managed identity" is the cleaner
   long-term choice and the bicep already grants the role, but the
   MI-based connection occasionally returns a stubborn 403 in
   Foundry even with the role in place. Use API key for the
   workshop; revisit later if you want MI everywhere.
4. **Name:** leave the default (`<search-service>`) and **Create**.

You only do this once per Foundry project, not once per agent.

### 4b. Create the agent

**Build → Agents → + New agent**:

- **Name:** `noclar-grounded`
- **Model:** `gpt-5-mini`
- **Instructions:** paste
  [`src/labs/prompts/grounded.md`](../../src/labs/prompts/grounded.md).
  Note the explicit rules to (i) extract filter hints from the
  user's phrasing, (ii) issue a hybrid query, (iii) cite every
  factual claim by `document_id`.
- **Tools → Knowledge → Azure AI Search:** pick the connection you
  just created, pick the `noclar-corpus` index, and set **Query type
  = Hybrid + semantic**. The four options the portal offers are:

  | Option | Uses | When to pick it |
  |---|---|---|
  | Simple | BM25 only | exact-phrase / structured lookups (norm IDs, contract numbers) |
  | Semantic | BM25 + L2 re-ranker | NL questions, no vector field needed |
  | Hybrid (vector + keyword) | BM25 ⊕ ANN via RRF | NL questions, no semantic quota left |
  | **Hybrid + semantic** | BM25 ⊕ ANN ⊕ L2 re-ranker | **default for this lab** |

  The free semantic plan (`semanticSearch: 'free'` in the bicep)
  covers 1,000 queries/month — more than enough for a 20-person
  workshop. The 100–200 ms re-rank latency is invisible next to the
  agent's own generation time.
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

bash:

```bash
python -m src.labs.lab03.ground_query \
  "What requirements does the anti-bribery policy impose..." \
  --document-type policy

python -m src.labs.lab03.ground_query \
  "What does the regulatory guidance say about reporting..." \
  --document-type regulation

python -m src.labs.lab03.ground_query \
  "How large were the bonus payments to the management board?"
```

PowerShell:

```powershell
python -m src.labs.lab03.ground_query `
  "What requirements does the anti-bribery policy impose..." `
  --document-type policy

python -m src.labs.lab03.ground_query `
  "What does the regulatory guidance say about reporting..." `
  --document-type regulation

python -m src.labs.lab03.ground_query `
  "How large were the bonus payments to the management board?"
```

The CLI prints the hybrid top-k *and* the agent's cited answer.

## 6. Run Content Understanding on a contract (10 min)

Content Understanding lives in **its own portal**, not inside
`ai.azure.com`. It also doesn't accept Markdown — its analyzers run on
PDF / DOCX / image input. The repo ships
`data/sample-docs/contract-excerpt-consultancy.pdf` (rendered from the
`.md` you indexed in §2) for exactly this step.

1. Open <https://contentunderstanding.ai.azure.com/> and pick your
   Foundry project (the picker in the top right uses the same project
   list as `ai.azure.com`).
2. **Analyzers → + New analyzer**.
3. **Source type:** *Document*.
4. **Upload sample:** `data/sample-docs/contract-excerpt-consultancy.pdf`.
   The portal needs a sample *before* you can define a schema —
   that's the intended UX, the schema editor previews extraction
   against the sample as you go.
5. **Name:** `consultancycontract` (no hyphen — the portal silently
   strips non-alphanumerics, and our §8 code looks the ID up
   verbatim).
6. **Define the schema** — add these six fields (start from a blank
   schema; the portal's "suggest schema" autopilot is optional and
   tends to over-generate):

   | Field | Type | Notes |
   |---|---|---|
   | `parties` | String | Both legal entities, free-text. |
   | `effective_date` | Date | ISO date if present, else null. |
   | `total_value_eur` | Number | Monthly retainer × 12 if no fixed total. |
   | `success_fee_percent` | Number | Percentage as a plain number (e.g. `4`). |
   | `deliverable_required_before_payment` | String | `"yes"` / `"no"` / `"unclear"`. |
   | `governing_law` | String | Jurisdiction name. |

7. **Test** — the panel on the right shows the extracted JSON over
   your uploaded sample. Iterate on the field descriptions if a value
   comes back wrong; descriptions are the prompt.
8. **Build analyzer** — click the **Build analyzer** button (top right
   of the schema editor). This is what actually registers the
   analyzer ID on the Foundry account so it's callable from code; up
   to this point you've only been previewing against the sample.
   Wait for the status to flip to *Ready* (10–30 s).
9. **Save.** The portal will offer a one-click *"View code"* sample —
   our §8 helper already encodes the same call, so you can close it.

## 7. Compare RAG vs extraction (5 min)

Back in **`ai.azure.com` → Build → Agents → `noclar-grounded` →
Playground**, ask:

> *"Which success-fee clause applies to the consultancy contract,
> and what percentage?"*

Expect a sentence or two of prose that names the **4% success fee**
and carries a `[contract-excerpt-consultancy]` citation.

Now switch tabs back to Content Understanding and look at the test
panel — same source document, but the answer comes back as
`"success_fee_percent": 4` in the JSON. Same fact, two different
shapes.

> **When do you want which?** Prose with citations preserves
> context; the structured field is what a downstream system can
> *act* on. In production, you usually want both: extraction for the
> deterministic field that drives a workflow, RAG for the
> human-readable narrative around it.

## 8. Feed the extract back into Lab 02 (5 min)

`IntakeFacts.documented_facts` is a `list[str]` — one bullet per
piece of evidence, written into **Section 3 (Facts of the case)** of
the final memo. The exercise: have the orchestrator actually *call*
the analyzer you built in §6 (over the CU REST API) and append the
extracted facts as one bullet — then re-run Lab 02 and find your new
bullet in the draft memo.

`src/labs/lab02/orchestrator.py` ships with two **`# Lab 03 §8`**
blocks pre-written and commented out: a helper
`_call_content_understanding()` near the top of the file, and a call
site right after `_interactive_intake(...)` in `main()`.

1. Open `src/labs/lab02/orchestrator.py`.
2. Search for `# Lab 03 §8`. **Uncomment** both blocks:
   - The body of `_call_content_understanding()` (everything between
     the `--- Lab 03 §8: uncomment this body ---` marker and the
     `raise NotImplementedError(...)` — delete that raise too).
   - The call site in `main()` (the `cu_fields = ...` block and the
     `intake_facts.documented_facts.append(...)` that follows).
3. Save.
4. Re-run Lab 02:

   bash:

   ```bash
   python -m src.labs.lab02.orchestrator --tip-file data/sample-docs/tip.md
   ```

   PowerShell:

   ```powershell
   python -m src.labs.lab02.orchestrator --tip-file data/sample-docs/tip.md
   ```

5. After intake, you'll see `Content Understanding extracted: {...}`
   with the analyzer's structured output. Approve through the HITL
   checkpoints. In the final memo (Section 3), the
   CU-derived sentence sits alongside the bullets the intake agent
   pulled from the tip paragraph.

What the helper does under the hood:

- Constructs the Foundry account endpoint (`https://<account>.services.ai.azure.com/` — derived by stripping the `/api/projects/...` suffix off `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT`).
- Uses the `azure-ai-contentunderstanding` SDK with `DefaultAzureCredential` to call `begin_analyze_binary(...)`, passing the raw PDF bytes — no blob upload required.
- Strips the `{ "valueString": "...", "valueNumber": ... }` envelope CU wraps each field in.

That's the loop in production: extraction agents drop deterministic
fields into `documented_facts`, intake & RAG fill in context, the
human still approves at the HITL gate. Lab 04 takes the next step
and wires extractors as **hosted agent tools** so the orchestrator
doesn't even need to know which extractor ran.

---

## ✅ Done when

- [ ] `noclar-corpus` index exists with N chunks across the 6
      sample docs, a `default` semantic configuration, and an
      `AzureOpenAIVectorizer` on the vector profile.
- [ ] `noclar-grounded` agent exists with the corpus connected and
      **Hybrid + semantic** selected as the query type.
- [ ] All three test queries returned the expected behaviour
      (one filtered, one declined).
- [ ] A Content Understanding analyser ran on the contract.
- [ ] The orchestrator's `# Lab 03 §8` blocks are uncommented and
      the re-run shows the CU-extracted sentence in Section 3 of
      the memo.
