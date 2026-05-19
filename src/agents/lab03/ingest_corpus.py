"""Lab 03 — Azure AI Search ingest for the `noclar-corpus` hybrid index.

Reads every Markdown file under `data/sample-docs/`, parses its YAML
front-matter for structured metadata, chunks the body by paragraph,
embeds each chunk with the Foundry-hosted embedding deployment, and
uploads the documents to an Azure AI Search index `noclar-corpus`.

The index uses a **hybrid** schema — keyword (BM25) on `chunk_text`,
vector on `chunk_vector`, plus filterable structured fields
(`document_type`, `language`, `jurisdiction`, `effective_date`).

Ships **fully commented**. Lab 03 step 1 uncomments this file.

Run (after uncommenting):

    pip install -r src/agents/lab03/requirements.txt
    python -m src.agents.lab03.ingest_corpus

Required env vars:

    AZURE_SEARCH_ENDPOINT           https://<svc>.search.windows.net
    AZURE_SEARCH_INDEX_NAME         noclar-corpus
    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT
    AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT_NAME  e.g. text-embedding-3-small
"""

# from __future__ import annotations
#
# import os
# import re
# from pathlib import Path
#
# import yaml
# from azure.identity import DefaultAzureCredential
# from azure.search.documents import SearchClient
# from azure.search.documents.indexes import SearchIndexClient
# from azure.search.documents.indexes.models import (
#     HnswAlgorithmConfiguration,
#     SearchableField,
#     SearchField,
#     SearchFieldDataType,
#     SearchIndex,
#     SimpleField,
#     VectorSearch,
#     VectorSearchProfile,
# )
# from openai import AzureOpenAI
#
# INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "noclar-corpus")
# EMBEDDING_DIM = 1536  # text-embedding-3-small
# CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "sample-docs"
#
# _FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
#
#
# def _parse_doc(path: Path) -> tuple[dict, str]:
#     text = path.read_text(encoding="utf-8")
#     m = _FRONT_MATTER.match(text)
#     if not m:
#         raise ValueError(f"{path.name}: missing YAML front-matter")
#     meta = yaml.safe_load(m.group(1)) or {}
#     body = m.group(2).strip()
#     return meta, body
#
#
# def _chunk(body: str, max_chars: int = 1200) -> list[str]:
#     # Naive paragraph chunker — good enough for a ~6-doc corpus.
#     paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
#     chunks, current = [], ""
#     for p in paragraphs:
#         if len(current) + len(p) + 2 > max_chars and current:
#             chunks.append(current.strip())
#             current = p
#         else:
#             current = f"{current}\n\n{p}" if current else p
#     if current.strip():
#         chunks.append(current.strip())
#     return chunks
#
#
# def _build_index_client() -> SearchIndexClient:
#     endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
#     return SearchIndexClient(endpoint=endpoint, credential=DefaultAzureCredential())
#
#
# def _build_search_client() -> SearchClient:
#     endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
#     return SearchClient(
#         endpoint=endpoint, index_name=INDEX_NAME, credential=DefaultAzureCredential()
#     )
#
#
# def _build_embedding_client() -> AzureOpenAI:
#     # The Foundry project exposes an Azure-OpenAI-compatible inference
#     # endpoint under its `models` route. We use the same DefaultAzureCredential
#     # token; AzureOpenAI accepts a bearer-token provider.
#     endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
#     # Trim trailing /api/projects/<name> if present — embeddings live at the
#     # account-level inference endpoint.
#     base = re.sub(r"/api/projects/[^/]+/?$", "", endpoint).rstrip("/")
#     token_provider = _bearer_token_provider()
#     return AzureOpenAI(
#         api_version="2024-10-21",
#         azure_endpoint=base,
#         azure_ad_token_provider=token_provider,
#     )
#
#
# def _bearer_token_provider():
#     cred = DefaultAzureCredential()
#
#     def _provider() -> str:
#         return cred.get_token("https://cognitiveservices.azure.com/.default").token
#
#     return _provider
#
#
# def _ensure_index(client: SearchIndexClient) -> None:
#     fields = [
#         SimpleField(name="id", type=SearchFieldDataType.String, key=True),
#         SimpleField(
#             name="document_id", type=SearchFieldDataType.String, filterable=True
#         ),
#         SearchableField(name="title", type=SearchFieldDataType.String),
#         SimpleField(
#             name="document_type",
#             type=SearchFieldDataType.String,
#             filterable=True,
#             facetable=True,
#         ),
#         SimpleField(
#             name="language", type=SearchFieldDataType.String, filterable=True
#         ),
#         SimpleField(
#             name="jurisdiction",
#             type=SearchFieldDataType.String,
#             filterable=True,
#         ),
#         SimpleField(
#             name="effective_date",
#             type=SearchFieldDataType.DateTimeOffset,
#             filterable=True,
#             sortable=True,
#         ),
#         SearchableField(name="chunk_text", type=SearchFieldDataType.String),
#         SearchField(
#             name="chunk_vector",
#             type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#             searchable=True,
#             vector_search_dimensions=EMBEDDING_DIM,
#             vector_search_profile_name="default",
#         ),
#     ]
#     vector_search = VectorSearch(
#         algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
#         profiles=[
#             VectorSearchProfile(
#                 name="default", algorithm_configuration_name="default-hnsw"
#             )
#         ],
#     )
#     index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
#     try:
#         client.delete_index(INDEX_NAME)
#     except Exception:
#         pass
#     client.create_index(index)
#     print(f"  created index: {INDEX_NAME}")
#
#
# def _embed(client: AzureOpenAI, deployment: str, texts: list[str]) -> list[list[float]]:
#     resp = client.embeddings.create(model=deployment, input=texts)
#     return [d.embedding for d in resp.data]
#
#
# def main() -> None:
#     print(f"Ingesting from {CORPUS_DIR}")
#     index_client = _build_index_client()
#     _ensure_index(index_client)
#
#     search_client = _build_search_client()
#     embedding_client = _build_embedding_client()
#     embedding_deployment = os.environ["AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT_NAME"]
#
#     docs: list[dict] = []
#     doc_count = 0
#     for path in sorted(CORPUS_DIR.glob("*.md")):
#         if path.name.lower() == "readme.md":
#             continue
#         meta, body = _parse_doc(path)
#         chunks = _chunk(body)
#         if not chunks:
#             continue
#         vectors = _embed(embedding_client, embedding_deployment, chunks)
#         for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
#             docs.append(
#                 {
#                     "id": f"{meta['document_id']}-{idx:03d}",
#                     "document_id": meta["document_id"],
#                     "title": meta.get("title", path.stem),
#                     "document_type": meta.get("document_type", "unknown"),
#                     "language": meta.get("language", "en"),
#                     "jurisdiction": meta.get("jurisdiction", "global"),
#                     "effective_date": str(meta.get("effective_date", "2020-01-01"))
#                     + "T00:00:00Z",
#                     "chunk_text": chunk,
#                     "chunk_vector": vector,
#                 }
#             )
#         doc_count += 1
#
#     if not docs:
#         print("  no chunks to upload")
#         return
#     search_client.upload_documents(documents=docs)
#     print(f"Indexed {len(docs)} chunks across {doc_count} documents")
#
#
# if __name__ == "__main__":
#     main()
