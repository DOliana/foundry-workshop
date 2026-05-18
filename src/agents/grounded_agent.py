"""Grounded knowledge agent — RAG over Azure AI Search (Block 3).

Wires the agent to a Foundry-IQ-backed Azure AI Search index that holds the
indexed sample NOCLAR corpus. Citations are required by the prompt.
"""

from __future__ import annotations

from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import AzureAISearchTool, ToolSet
from azure.identity import DefaultAzureCredential

from src.shared.config import get_settings

PROMPT_PATH = Path(__file__).parent / "prompts" / "grounded.md"

DEFAULT_INDEX_NAME = "noclar-corpus"


def build_grounded_agent(
    search_connection_name: str,
    index_name: str = DEFAULT_INDEX_NAME,
) -> dict[str, str]:
    """Create the grounded agent. `search_connection_name` is the name of the
    Azure AI Search connection registered on the Foundry project (added by
    `scripts/seed_foundry_project.py`).
    """

    settings = get_settings()
    client = AgentsClient(
        endpoint=settings.foundry_project_endpoint,
        credential=DefaultAzureCredential(),
    )

    toolset = ToolSet()
    toolset.add(
        AzureAISearchTool(
            index_connection_id=search_connection_name,
            index_name=index_name,
            top_k=5,
        )
    )

    agent = client.create_agent(
        model=settings.foundry_model_deployment,
        name="noclar-grounded",
        description="Cited grounding over the NOCLAR corpus",
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        toolset=toolset,
    )
    return {"agent_id": agent.id, "name": agent.name}


if __name__ == "__main__":
    raise SystemExit(
        "Run `python scripts/seed_foundry_project.py` to provision the grounded agent."
    )
