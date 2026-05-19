# Sample NOCLAR Corpus — README

> **Disclaimer:** Every document in this folder is **fictional**. Company names, individuals, contracts, payments and regulatory references are invented for workshop purposes only. Any resemblance to real organizations or events is coincidental. Do not use this content for any real engagement.

## Fictional setting

- **Audit client:** *Helios Industrieanlagen GmbH* (Helios) — a mid-sized German manufacturer of industrial heating systems headquartered in Stuttgart.
- **Audit firm:** *Beispiel & Partner Wirtschaftsprüfungsgesellschaft*
- **Engagement partner:** Dr. Lena Hartmann
- **Engagement period:** Statutory audit FY2025 (calendar year)

## File index

| File | Language | Type | Used in |
|---|---|---|---|
| `tip.md` | EN | One-paragraph intake tip (the fixture participants paste in Lab 02) | Lab 02 |
| `intake-email-01-anonymous-tip.md` | EN | Anonymous tipster email (supplementary reading) | Lab 03 |
| `intake-email-02-internal-whistleblower.md` | EN | Internal whistleblower email | Lab 03 |
| `witness-statement-procurement-lead.md` | EN | Recorded witness statement | Lab 03 |
| `contract-excerpt-consultancy.md` | EN | Excerpt of a consultancy agreement | Lab 03 (RAG + Content Understanding) |
| `payment-ledger-extract.md` | EN | Extract of payment ledger entries | Lab 03 |
| `regulatory-isa250.md` | EN | Simplified ISA 250 NOCLAR-style guidance (paraphrased) | Lab 03 |
| `regulatory-idw-ps210.md` | EN | Simplified IDW PS 210-style guidance (paraphrased) | Lab 03 |
| `internal-policy-anti-bribery.md` | EN | Internal anti-bribery policy excerpt | Lab 03 |

Every file ships with **YAML front-matter** (`document_id`,
`document_type`, `language`, `jurisdiction`, `effective_date`,
`title`) that the Lab 03 ingest script parses to populate the
filterable / facetable fields of the Search index.

## How it is used

- **Lab 02** — participants paste `tip.md` as their input.
- **Lab 03** — `src/agents/lab03/ingest_corpus.py` reads every file
  in this folder, chunks the body, embeds each chunk with the
  Foundry embedding deployment, and uploads to Azure AI Search.
- **Lab 03** — Content Understanding extracts structured fields
  from `contract-excerpt-consultancy.md`.
