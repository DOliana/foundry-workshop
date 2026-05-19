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

from __future__ import annotations

import asyncio
import json
import numbers
import os
import re
from datetime import datetime
from pathlib import Path

from agent_framework.foundry import FoundryAgent
from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

DATASET = Path(__file__).resolve().parents[3] / "data" / "eval" / "grounding-citations.jsonl"
RESULTS_DIR = Path(__file__).resolve().parents[3] / "data" / "eval"
GROUNDED_AGENT = "noclar-grounded"


def _judge_config() -> dict:
    return {
        "azure_endpoint": re.sub(
            r"/api/projects/[^/]+/?$",
            "",
            os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"],
        ).rstrip("/"),
        "azure_deployment": os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT"],
        "api_version": os.environ.get("AZURE_FOUNDRY_API_VERSION", "2024-10-21"),
    }


async def _ask_agent(agent, query: str) -> str:
    result = await agent.run(query)
    return result.text


def _extract_score(value) -> float:
    if isinstance(value, numbers.Real):
        return float(value)
    if isinstance(value, dict):
        for key in ("score", "groundedness", "relevance", "value"):
            if key in value:
                return _extract_score(value[key])
    return 0.0


async def run() -> None:
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"\n{'='*70}")
    print(f"Evaluating {len(rows)} queries against '{GROUNDED_AGENT}'")
    print(f"{'='*70}\n")

    judge = _judge_config()
    groundedness = GroundednessEvaluator(model_config=judge)
    relevance = RelevanceEvaluator(model_config=judge)

    out: list[dict] = []
    project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
    async with DefaultAzureCredential() as credential:
        async with AIProjectClient(endpoint=project_endpoint, credential=credential) as projects:
            agent = FoundryAgent(project_client=projects, agent_name=GROUNDED_AGENT)
            for idx, row in enumerate(rows):
                query = row["query"]
                context = row.get("context", "")
                answer = await _ask_agent(agent, query)
                g_result = groundedness(response=answer, context=context, query=query)
                r_result = relevance(response=answer, query=query)
                g_score = _extract_score(g_result)
                r_score = _extract_score(r_result)
                print(f"  [{idx+1:02d}] groundedness={g_score:.2f} | relevance={r_score:.2f} | Q: {query[:50]}...")
                out.append(
                    {
                        "query": query,
                        "expected_answer": row.get("expected_answer"),
                        "expected_citation": row.get("expected_citation"),
                        "actual_answer": answer,
                        "groundedness": g_score,
                        "relevance": r_score,
                    }
                )

    # Calculate statistics
    avg_groundedness = sum(r["groundedness"] for r in out) / len(out) if out else 0
    avg_relevance = sum(r["relevance"] for r in out) / len(out) if out else 0
    
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total evaluated: {len(out)}")
    print(f"Average groundedness: {avg_groundedness:.2f}")
    print(f"Average relevance: {avg_relevance:.2f}")
    print()
    
    # Print first few results
    print("Sample Results (first 2):")
    print("-" * 70)
    for result in out[:2]:
        print(f"\nQuery: {result['query']}")
        print(f"Answer: {result['actual_answer'][:120]}...")
        print(f"Groundedness: {result['groundedness']:.2f} | Relevance: {result['relevance']:.2f}")

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"results-{ts}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'='*70}")
    print(f"Full results saved to: {out_path}")
    print(f"{'='*70}\n")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
