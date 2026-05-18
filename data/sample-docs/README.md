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
| `intake-email-01-anonymous-tip.md` | EN | Anonymous tipster email | Block 1, 3 |
| `intake-email-02-internal-whistleblower.md` | EN | Internal whistleblower email | Block 1, 3 |
| `witness-statement-procurement-lead.md` | EN | Recorded witness statement | Block 3 |
| `contract-excerpt-consultancy.md` | EN | Excerpt of a consultancy agreement | Block 3 |
| `payment-ledger-extract.md` | EN | Extract of payment ledger entries | Block 3 |
| `regulatory-isa250.md` | EN | Simplified ISA 250 NOCLAR-style guidance (paraphrased) | Block 3 |
| `regulatory-idw-ps210.md` | EN | Simplified IDW PS 210-style guidance (paraphrased) | Block 3 |
| `internal-policy-anti-bribery.md` | EN | Internal Helios anti-bribery policy excerpt | Block 3 |

## How it is used

- Block 3 indexes this folder into Azure AI Search via Foundry IQ.
- Block 3 also runs Content Understanding extraction on the intake emails and witness statement to produce structured facts.
- Block 2 / Block 4 agents reference the structured facts when drafting the Initial Assessment Memo.
