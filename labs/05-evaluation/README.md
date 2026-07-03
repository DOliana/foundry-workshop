# Lab 05 — Evaluation, Governance & Production Readiness

**Duration:** 50 minutes (Block 5)
**Outcome:** Run the **same evaluation twice — once from
the Foundry portal, once from the Azure AI Evaluation SDK** — against
the `noclar-grounded` agent from Lab 03, compare the two, walk
through the day's traces in Application Insights, and close on a
production-hardening discussion.

---

## Why two paths?

- **Portal** is what an analyst would use for a one-off, no-code
  exploratory eval.
- **SDK** is what goes into a CI pipeline for regression / gating.

Running both back-to-back over the same dataset gives a feel for
what each is best suited for and shows the scores converge (the
judge is non-deterministic, so expect ±1 on integer scales).

---

## 1. Uncomment and install

| File | Purpose |
|---|---|
| `src/labs/lab05/run_eval.py` | SDK-driven evaluation script. |

```bash
python -m py_compile src/labs/lab05/run_eval.py
pip install -r src/labs/lab05/requirements.txt
```

## 2. Run the eval from the portal (15 min — primary)

1. **Open** <https://ai.azure.com>
2. **Evaluations → Create**.
3. **Target:** `noclar-grounded` (from Lab 03). The agent is more
   interesting than a raw model because its prompt + grounding tool
   both contribute to the score.
4. **Dataset:** 
   1. upload `data/eval/grounding-citations.jsonl`.
   2. name it 'noclar-grounding-citations'
5. **Field mapping**
   1. **Judge model:** keep the default (`gpt-4.1` or whichever the portal preselects). The judge is independent of the agent under test.
   2. Query: `{{item.query}}`
   3. Response: not available
   4. Context: `{{item.expected_documents}}`
   5. Ground truth: `{{item.ground_truth}}`
   6. Tool calls: not available
   7. Tool definitions: not available
6. **Criteria:** **Groundedness**, **Relevance**, **HateAndUnfairness** (remove the agent criteria - the more evaluators the longer it takes...).
7. **Name:** keep the default 
8. **Run.** Wait ~1–2 min.

Walk the results:

- Per-row scores **with the judge's reasoning** expanded.
- Aggregated metrics across the dataset.
- Side-by-side input → output → expected → score.
- Failed rows flagged.

> **Sanity check.** At least one row should fail in an
> interpretable way (e.g. the agent didn't cite, or cited the wrong
> doc). If everything passes, the dataset is too easy — flag this
> to the instructor.

## 3. Run the same eval from the SDK (10 min)

```bash
python -m src.labs.lab05.run_eval
```

The script reads the same JSONL, calls `noclar-grounded`, scores
with the same evaluators, and writes
`data/eval/results-<timestamp>.json`.

Compare scores side-by-side with the portal run. ±1 on integer
scales is expected.

> **Discussion.** Portal eval = one-off, exploratory, no-code, fast
> turn-around for an analyst. SDK eval = CI, regression, automatable
> gates on PRs. They are complementary, not redundant.

## 4. Walk the day's traces in App Insights (5 min)

**Application Map** — point at the spans that light up for each
lab:

- Lab 01 — a single LLM span per playground call.
- Lab 02 — a multi-agent tree with the three sub-agent spans + the
  two Function calls.
- Lab 03 — agent → AI Search → agent.
- Lab 04 — agent → Function → queue → Function; plus the MCP
  tool calls.

Drill into one trace, expand spans, point out tool calls, token
counts, and the `content_filter` event from Lab 01.

## 5. Production hardening checklist (10 min)

| Concern | Workshop posture | Production posture |
|---|---|---|
| **Identity** | Default Azure Credential, function keys. | Managed identities everywhere; remove function keys; put APIM in front. |
| **Network** | Public endpoints. | Private endpoints; VNet integration on Functions, Foundry, Search, Storage. |
| **Secrets** | `.env` + function keys. | Key Vault references; no secrets in env. |
| **Logging** | App Insights default tier. | Diagnostic settings to Log Analytics + immutable archive; retention per policy. |
| **HITL UI** | Terminal `approve` prompt. | A real reviewer queue UI (Teams / web) with role-gated approvals. |
| **Memo storage** | Blob with `approved_by`. | Versioned blob + WORM lock for the regulatory retention window. |
| **Voice channel** | Internet-only Voice Live demo (laptop mic ↔ Foundry over WSS). | If telephony is in scope, add Azure Communication Services + a phone number, recording consent, and DLP scrubbing pre-storage. |
| **Eval** | Manual portal + SDK run. | Eval gates in CI; alerts on metric regressions. |
| **Knowledge base** | One Search index. | Per-tenant indexes; index aliasing for blue/green ingest swaps. |

## 6. Tying it back (5 min)

The artefact-by-artefact audit trail you have at the end of the
day:

- One `log_request` blob per conversation, with prompt + response.
- Every memo in `assessments/` with `approved_by` + `approved_at`.
- Every grounded answer cites by `document_id` (Lab 03).
- Every classification has a confidence score (Lab 02 specialist
  agent).
- Every eval run writes a frozen-dataset JSON file with scores +
  the judge's reasoning.

That trail is what makes the workflow defensible — every claim is
traceable to (a) the model, (b) the source document, (c) the human
who approved it, (d) the eval score at the time the model was
deployed.

---

## ✅ Done when

- [ ] You ran the portal eval and inspected per-row reasoning.
- [ ] You ran the SDK eval and compared scores.
- [ ] You walked one App Insights trace and identified spans for
      each lab.
- [ ] You can articulate one item from the hardening checklist
      that *your* environment is closest to needing.
