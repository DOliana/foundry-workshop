# System prompts

This folder contains the system prompts used by each agent role. Keeping prompts in version-controlled files (rather than inline strings) makes them reviewable, evaluatable, and translatable.

| File | Used by |
|---|---|
| `intake.md` | `noclar-intake` — guided NOCLAR intake (Lab 01) |
| `grounded.md` | `noclar-grounded` — RAG/grounding agent (Lab 03) |
| `orchestrator.md` | `noclar-orchestrator` — LLM-driven workflow agent (Lab 04) |
| `legal_classifier.md` | `noclar-legal-classifier` — specialist agent for legal classification (Lab 02) |
| `drafter.md` | `noclar-drafter` — specialist agent that drafts the memo (Lab 02) |
| `voice_intake.md` | Voice Live demo system prompt (Lab 04, instructor demo) |

All agents are created in the Foundry portal during the labs (or in one shot by [`scripts/seed_foundry_project.py`](../../../scripts/seed_foundry_project.py) for instructor pre-warming).
