# """Lab 03 — hybrid grounded query CLI.

# Issues a hybrid Azure AI Search query (text + vector + optional
# structured `$filter`), prints the top-k chunks with their scores, then
# runs the same query through the Foundry `noclar-grounded` agent and
# prints its cited answer.

# Ships **fully commented**. Lab 03 step 1 uncomments this file.

# Run (after uncommenting):

#     python -m src.labs.lab03.ground_query "What does the anti-bribery policy require?"
#     python -m src.labs.lab03.ground_query "..." --document-type policy --language en
#     python -m src.labs.lab03.ground_query "..." --jurisdiction EU
# """

# from __future__ import annotations

# import argparse
# import asyncio
# import os

# from agent_framework.foundry import FoundryAgent
# from azure.ai.projects.aio import AIProjectClient
# from azure.identity import DefaultAzureCredential as SyncCredential
# from azure.identity.aio import DefaultAzureCredential
# from azure.search.documents import SearchClient
# from azure.search.documents.models import VectorizableTextQuery

# INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "noclar-corpus")
# GROUNDED_AGENT = "noclar-grounded"


# def _search_client() -> SearchClient:
#     return SearchClient(
#         endpoint=os.environ["AZURE_AI_SEARCH_ENDPOINT"],
#         index_name=INDEX_NAME,
#         credential=SyncCredential(),
#     )


# def _build_filter(args: argparse.Namespace) -> str | None:
#     parts: list[str] = []
#     if args.document_type:
#         parts.append(f"document_type eq '{args.document_type}'")
#     if args.language:
#         parts.append(f"language eq '{args.language}'")
#     if args.jurisdiction:
#         parts.append(f"jurisdiction eq '{args.jurisdiction}'")
#     return " and ".join(parts) if parts else None


# def _vector_query(query: str, k: int = 10) -> VectorizableTextQuery:
#     # The kwarg for "number of nearest neighbours" was renamed across
#     # `azure-search-documents` releases (`k` in 11.7.0b2, `k_nearest_neighbors`
#     # in 11.6.0 / 11.5.x). Construct, then set whichever python attribute the
#     # installed version actually exposes — works across both.
#     vq = VectorizableTextQuery(text=query, fields="chunk_vector")
#     attr_map = getattr(vq, "_attribute_map", {})
#     for name in ("k_nearest_neighbors", "k"):
#         if name in attr_map:
#             setattr(vq, name, k)
#             return vq
#     # Last-resort fallback: set both; msrest will serialise whichever is in the map.
#     vq.k_nearest_neighbors = k  # type: ignore[attr-defined]
#     vq.k = k  # type: ignore[attr-defined]
#     return vq


# def _hybrid_search(query: str, args: argparse.Namespace) -> list[dict]:
#     # The index's vector profile has an AzureOpenAIVectorizer attached, so
#     # we send the *text* and let AI Search embed it server-side at query
#     # time using the Foundry embedding deployment. This mirrors what the
#     # Foundry agent does over the same connection.
#     filter_expr = _build_filter(args)
#     client = _search_client()
#     results = client.search(
#         search_text=query,
#         vector_queries=[_vector_query(query, k=10)],
#         filter=filter_expr,
#         top=args.top_k,
#         select=["document_id", "title", "document_type", "language", "chunk_text"],
#     )
#     return [dict(r) for r in results]


# async def _ask_grounded_agent(query: str) -> str:
#     project_endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
#     async with DefaultAzureCredential() as credential:
#         async with AIProjectClient(endpoint=project_endpoint, credential=credential) as projects:
#             agent = FoundryAgent(project_client=projects, agent_name=GROUNDED_AGENT)
#             result = await agent.run(query)
#             return result.text


# def main() -> None:
#     parser = argparse.ArgumentParser(description="Hybrid grounded query.")
#     parser.add_argument("query", help="Natural-language question.")
#     parser.add_argument("--document-type", help="e.g. policy, regulation, contract")
#     parser.add_argument("--language", help="e.g. en, de")
#     parser.add_argument("--jurisdiction", help="e.g. EU, HR, global")
#     parser.add_argument("--top-k", type=int, default=5)
#     parser.add_argument("--no-agent", action="store_true", help="Skip agent call.")
#     args = parser.parse_args()

#     print("\n--- Hybrid search top-k ---")
#     for r in _hybrid_search(args.query, args):
#         print(
#             f"  [{r.get('document_type')}] {r.get('document_id')} :: "
#             f"{r.get('title')}"
#         )
#         print(f"    {r['chunk_text'][:160]}...")

#     if args.no_agent:
#         return

#     print("\n--- noclar-grounded agent answer ---")
#     answer = asyncio.run(_ask_grounded_agent(args.query))
#     print(answer)


# if __name__ == "__main__":
#     main()
