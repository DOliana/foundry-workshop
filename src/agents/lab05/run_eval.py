"""Lab 05 — SDK-based evaluation against `noclar-grounded`.

Reads `data/eval/grounding-citations.jsonl`, calls the hosted
`noclar-grounded` agent once per row, scores each response with the
`azure-ai-evaluation` `GroundednessEvaluator` and `RelevanceEvaluator`,
and writes results to `data/eval/results-<timestamp>.json`.

Ships **fully commented**. Lab 05 step 1 uncomments this file.

Run (after uncommenting):

    pip install -r src/agents/lab05/requirements.txt
    python -m src.agents.lab05.run_eval

Required env vars:

    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT
    AZURE_FOUNDRY_MODEL_DEPLOYMENT_NAME    e.g. gpt-4.1-mini
    AZURE_FOUNDRY_API_VERSION              e.g. 2024-10-21
"""

# from __future__ import annotations
#
# import asyncio
# import json
# import os
# import re
# from datetime import datetime
# from pathlib import Path
#
# from agent_framework.foundry import FoundryAgent
# from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator
# from azure.ai.projects.aio import AIProjectClient
# from azure.identity.aio import DefaultAzureCredential
#
# DATASET = Path(__file__).resolve().parents[3] / "data" / "eval" / "grounding-citations.jsonl"
# RESULTS_DIR = Path(__file__).resolve().parents[3] / "data" / "eval"
# GROUNDED_AGENT = "noclar-grounded"
#
#
# def _judge_config() -> dict:
#     return {
#         "azure_endpoint": re.sub(
#             r"/api/projects/[^/]+/?$",
#             "",
#             os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"],
#         ).rstrip("/"),
#         "azure_deployment": os.environ["AZURE_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
#         "api_version": os.environ.get("AZURE_FOUNDRY_API_VERSION", "2024-10-21"),
#     }
#
#
# async def _ask_agent(agent, query: str) -> str:
#     result = await agent.run(query)
#     return result.text
#
#
# async def run() -> None:
#     rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
#     print(f"Loaded {len(rows)} eval rows from {DATASET}")
#
#     judge = _judge_config()
#     groundedness = GroundednessEvaluator(model_config=judge)
#     relevance = RelevanceEvaluator(model_config=judge)
#
#     out: list[dict] = []
#     project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
#     async with DefaultAzureCredential() as credential:
#         async with AIProjectClient(endpoint=project_endpoint, credential=credential) as projects:
#             agent = FoundryAgent(project_client=projects, agent_name=GROUNDED_AGENT)
#             for idx, row in enumerate(rows):
#                 query = row["query"]
#                 context = row.get("context", "")
#                 answer = await _ask_agent(agent, query)
#                 g = groundedness(response=answer, context=context, query=query)
#                 r = relevance(response=answer, query=query)
#                 print(f"  [{idx+1:02d}] groundedness={g} relevance={r}")
#                 out.append(
#                     {
#                         "query": query,
#                         "expected_answer": row.get("expected_answer"),
#                         "expected_citation": row.get("expected_citation"),
#                         "actual_answer": answer,
#                         "groundedness": g,
#                         "relevance": r,
#                     }
#                 )
#
#     ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
#     out_path = RESULTS_DIR / f"results-{ts}.json"
#     out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
#     print(f"Wrote results to {out_path}")
#
#
# def main() -> None:
#     asyncio.run(run())
#
#
# if __name__ == "__main__":
#     main()
