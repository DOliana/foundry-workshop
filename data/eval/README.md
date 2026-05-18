# Evaluation datasets

These JSONL files drive evaluation in Block 5 using the Azure AI Evaluation SDK.

| File | Purpose |
|---|---|
| `intake-extraction.jsonl` | Did the agent extract the right facts from the intake documents? |
| `memo-fields.jsonl` | Does the drafted memo contain the required fields with correct content? |
| `legal-classification.jsonl` | Did the agent identify the right legal norms (§ 299 StGB etc.)? |
| `grounding-citations.jsonl` | Are the agent's claims grounded in indexed documents (citation present + correct)? |

Each row is JSONL with at minimum: `query`, `ground_truth`, `expected_documents`, optional `tags`.
Use these as the input to `azure-ai-evaluation` runners shown in `labs/05-evaluation/`.
