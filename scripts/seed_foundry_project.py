"""Idempotent provisioning of the Foundry project for the workshop.

**Instructor-only helper.** Pre-warms an RG end-to-end so participants
can skip ahead if they fall behind. In the normal workshop flow,
participants build each artefact themselves:

  - Lab 01 creates `noclar-intake` in the portal.
  - Lab 02 creates `noclar-legal-classifier` + `noclar-drafter`.
  - Lab 03 runs `python -m src.labs.lab03.ingest_corpus`, creates
    the AI Search connection, and adds the `noclar-grounded` agent.
  - Lab 04 adds the `noclar-orchestrator` agent.

This script performs all of the above in one shot:

  - Uploads `data/sample-docs/` to the sample-docs container.
  - Creates the `noclar-corpus` AI Search index and indexes the corpus.
  - Creates/updates the five workshop agents (intake, grounded,
    legal-classifier, drafter, orchestrator) from the prompt files
    in `src/labs/prompts/`.

Run AFTER `azd provision`. Reads endpoint + names from
`azd env get-values`.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)
from azure.storage.blob import BlobServiceClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("seed-foundry-project")

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DOCS = REPO_ROOT / "data" / "sample-docs"
PROMPTS_DIR = REPO_ROOT / "src" / "labs" / "prompts"

INDEX_NAME = "noclar-corpus"
SEARCH_CONNECTION_NAME = "noclar-search"


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Env var {name} is required (run `azd env get-values > .env` first).")
    return v


def upload_sample_docs(blob_service: BlobServiceClient, container: str) -> int:
    client = blob_service.get_container_client(container)
    try:
        client.create_container()
    except ResourceExistsError:
        pass
    count = 0
    for path in sorted(SAMPLE_DOCS.glob("*.md")):
        blob = client.get_blob_client(path.name)
        blob.upload_blob(path.read_bytes(), overwrite=True)
        log.info("uploaded %s", path.name)
        count += 1
    return count


def ensure_search_index(search_endpoint: str, credential: DefaultAzureCredential) -> None:
    client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    existing = {idx.name for idx in client.list_indexes()}
    if INDEX_NAME in existing:
        log.info("index %s already exists", INDEX_NAME)
        return
    index = SearchIndex(
        name=INDEX_NAME,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="de.lucene"),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="language", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(name="title", type=SearchFieldDataType.String, searchable=True),
        ],
    )
    client.create_index(index)
    log.info("created index %s", INDEX_NAME)


def ingest_corpus(search_endpoint: str, credential: DefaultAzureCredential) -> int:
    from azure.search.documents import SearchClient

    client = SearchClient(
        endpoint=search_endpoint,
        index_name=INDEX_NAME,
        credential=credential,
    )
    docs = []
    for path in sorted(SAMPLE_DOCS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # Crude language detection: first frontmatter block "language: de" wins
        lang = "de" if "language: de" in text else "en"
        docs.append(
            {
                "id": path.stem,
                "document_id": path.name,
                "title": path.stem.replace("-", " ").title(),
                "content": text,
                "language": lang,
            }
        )
    result = client.upload_documents(documents=docs)
    log.info("indexed %d docs", sum(1 for r in result if r.succeeded))
    return len(docs)


def register_agents(client: AgentsClient, model_deployment: str) -> dict[str, str]:
    """Create or update the workshop agents. Returns {name: agent_id}."""

    def _instructions(name: str) -> str:
        return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")

    # Map of agent name -> (instructions filename, description).
    # All agents use response_format="auto" — the v1 Foundry Agents API
    # only accepts "auto" on this SDK; the prompts themselves instruct the
    # JSON-emitting agents (intake, classifier, drafter) to return a single
    # JSON object, which works reliably with the default sampling.
    specs = {
        "noclar-intake": ("intake", "Guided NOCLAR intake (chat + voice)"),
        "noclar-grounded": ("grounded", "Cited grounding over the NOCLAR corpus"),
        "noclar-legal-classifier": ("legal_classifier", "Proposes potentially violated norms"),
        "noclar-drafter": ("drafter", "Drafts the Initial Assessment Memo"),
        "noclar-orchestrator": ("orchestrator", "Top-level NOCLAR workflow"),
    }

    existing = {a.name: a for a in client.list_agents()}
    out: dict[str, str] = {}
    for name, (prompt_file, desc) in specs.items():
        instr = _instructions(prompt_file)
        kwargs: dict = {
            "model": model_deployment,
            "instructions": instr,
            "description": desc,
            "response_format": "auto",
        }
        if name in existing:
            updated = client.update_agent(agent_id=existing[name].id, **kwargs)
            out[name] = updated.id
            log.info("updated agent %s", name)
        else:
            agent = client.create_agent(name=name, **kwargs)
            out[name] = agent.id
            log.info("created agent %s", name)
    return out


def main() -> None:
    foundry_project = _env("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
    model = _env("AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT")
    storage_endpoint = _env("AZURE_STORAGE_BLOB_ENDPOINT")
    search_endpoint = _env("AZURE_AI_SEARCH_ENDPOINT")
    sample_docs_container = os.environ.get("SAMPLE_DOCS_CONTAINER", "sample-docs")

    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url=storage_endpoint, credential=credential)

    log.info("=== uploading sample-docs ===")
    upload_sample_docs(blob_service, sample_docs_container)

    log.info("=== ensuring search index ===")
    ensure_search_index(search_endpoint, credential)

    log.info("=== indexing corpus ===")
    ingest_corpus(search_endpoint, credential)

    log.info("=== registering agents ===")
    agents = AgentsClient(endpoint=foundry_project, credential=credential)
    ids = register_agents(agents, model)
    for n, i in ids.items():
        print(f"  {n}: {i}")

    print("\nSeed complete. Open the Foundry portal to inspect the project.")
    print()
    print("⚠️  Manual portal follow-up required for the JSON-emitting agents")
    print("    (noclar-intake, noclar-legal-classifier, noclar-drafter):")
    print()
    print("    1. Build → Agents → open the agent.")
    print("    2. Tools → delete the default Web Search / Grounding entry.")
    print("       (JSON-object response mode is incompatible with Web Search.)")
    print("    3. Response format → switch from 'auto' to 'JSON object' → Save.")
    print()
    print("    The Foundry v1 Agents SDK only accepts response_format='auto'")
    print("    on create/update, so the script cannot do steps 2–3 for you.")


if __name__ == "__main__":
    main()
