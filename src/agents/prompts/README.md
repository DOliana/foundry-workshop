# System prompts

This folder contains the system prompts used by each agent role. Keeping prompts in version-controlled files (rather than inline strings) makes them reviewable, evaluatable, and translatable.

| File | Used by |
|---|---|
| `intake.md` | `intake_agent.py` — guided NOCLAR intake |
| `grounded.md` | `grounded_agent.py` — RAG/grounding agent |
| `orchestrator.md` | `orchestrator.py` — top-level workflow agent |
| `legal_classifier.md` | specialist agent for legal classification |
| `drafter.md` | specialist agent that drafts the memo |
