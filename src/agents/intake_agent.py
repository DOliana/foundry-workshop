"""Intake agent — guided NOCLAR intake (Block 1).

This is the simplest agent in the workshop. Block 1 participants build this
themselves via the portal; this file is the *reference implementation* using
the Foundry Agents SDK so participants who fall behind have a working sample.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet
from azure.identity import DefaultAzureCredential

from src.agents.tools.functions_tools import log_request
from src.shared.config import get_settings

PROMPT_PATH = Path(__file__).parent / "prompts" / "intake.md"


def build_intake_agent() -> dict[str, str]:
    """Create the intake agent in the Foundry project. Idempotent on name."""

    settings = get_settings()
    client = AgentsClient(
        endpoint=settings.foundry_project_endpoint,
        credential=DefaultAzureCredential(),
    )

    toolset = ToolSet()
    toolset.add(FunctionTool(functions={log_request}))

    instructions = PROMPT_PATH.read_text(encoding="utf-8")

    agent = client.create_agent(
        model=settings.foundry_model_deployment,
        name="noclar-intake",
        description="Guided NOCLAR intake (AI Foundry workshop)",
        instructions=instructions,
        toolset=toolset,
    )

    return {"agent_id": agent.id, "name": agent.name}


def run_intake_conversation() -> None:
    """Tiny REPL for local interactive testing of the intake agent."""

    settings = get_settings()
    client = AgentsClient(
        endpoint=settings.foundry_project_endpoint,
        credential=DefaultAzureCredential(),
    )

    # Find or create the agent
    agents = list(client.list_agents())
    agent = next((a for a in agents if a.name == "noclar-intake"), None)
    if agent is None:
        info = build_intake_agent()
        agent = client.get_agent(info["agent_id"])

    thread = client.threads.create()
    conversation_id = str(uuid.uuid4())
    print(f"--- conversation {conversation_id} (thread {thread.id}) ---")
    print("Type 'exit' to quit.\n")

    # Seed the conversation_id so the agent passes it to log_request
    client.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"[system] conversation_id={conversation_id}, channel=chat, locale=en-US",
    )
    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break
        client.messages.create(thread_id=thread.id, role="user", content=user)
        run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        if run.status != "completed":
            print(f"[Run failed: {run.status} — {run.last_error}]")
            continue
        messages = list(client.messages.list(thread_id=thread.id))
        latest = next((m for m in messages if m.role == "assistant"), None)
        if latest:
            for content in latest.content:
                if content.type == "text":
                    print(f"Agent: {content.text.value}\n")


if __name__ == "__main__":
    run_intake_conversation()
