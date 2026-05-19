"""NOCLAR agent package — built on the Azure AI Foundry Agent Service.

Per-lab subpackages (each ships fully commented; uncommented by the lab):

  * `lab02.orchestrator`         — multi-agent + HITL workflow that
                                   produces an AssessmentMemo
  * `lab02.functions_tools`      — httpx wrappers around the Functions
                                   HTTP endpoints
  * `lab03.ingest_corpus`        — Azure AI Search hybrid index ingest
  * `lab03.ground_query`         — hybrid (text + vector + filter) CLI
  * `lab04.mcp_attach`           — Microsoft Learn MCP attach helper
  * `lab04.custom_tool`          — stub for your own function tool
  * `lab05.run_eval`             — SDK-driven groundedness/relevance run

Instructor-only helpers (kept at package root):
  * `intake_agent` / `grounded_agent` — programmatic agent creation
    scripts used by `scripts/seed_foundry_project.py`.
"""
