"""Lab 02 — register the two specialist agents idempotently.

A tiny "CI/CD" alternative to clicking through **Build → Agents → + New
agent** twice in the portal. Useful when:

  - You're re-running the workshop and want to reset the agents.
  - You want to see how a real pipeline would manage agents as code
    (prompt files in git, deploy via SDK, idempotent upserts).

Creates / updates:

  - ``noclar-legal-classifier`` from ``src/labs/prompts/legal_classifier.md``
  - ``noclar-drafter`` from ``src/labs/prompts/drafter.md``

Both with ``response_format=json_object``, no tools, no knowledge — same
settings the portal table in Lab 02 §2 specifies.

Run **after** ``azd provision`` and ``azd env get-values > .env``:

    python scripts/lab02_register_agents.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("lab02-register-agents")

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "src" / "labs" / "prompts"

AGENT_SPECS = {
    "noclar-legal-classifier": (
        "legal_classifier",
        "Proposes potentially violated norms for the NOCLAR memo.",
    ),
    "noclar-drafter": (
        "drafter",
        "Drafts the Initial Assessment Memo from intake + classification.",
    ),
}


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(
            f"Env var {name} is required. Run `azd env get-values > .env` "
            "first and source it (or use python-dotenv)."
        )
    return v


def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def main() -> None:
    _load_dotenv_if_present()

    endpoint = _env("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
    model = _env("AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT")

    client = AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())

    existing = {a.name: a for a in client.list_agents()}

    for name, (prompt_file, description) in AGENT_SPECS.items():
        instructions = (PROMPTS_DIR / f"{prompt_file}.md").read_text(encoding="utf-8")

        if name in existing:
            agent = client.update_agent(
                agent_id=existing[name].id,
                model=model,
                instructions=instructions,
                description=description,
                response_format="json_object",
            )
            log.info("updated %s (%s)", name, agent.id)
        else:
            agent = client.create_agent(
                model=model,
                name=name,
                description=description,
                instructions=instructions,
                response_format="json_object",
            )
            log.info("created %s (%s)", name, agent.id)

    print("\nDone. Open the Foundry portal → Build → Agents to verify.")


if __name__ == "__main__":
    main()
