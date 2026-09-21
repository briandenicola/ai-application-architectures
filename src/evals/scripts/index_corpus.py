#!/usr/bin/env python3
"""Create the Meridian search index and push the synthetic corpus into it.

ADR-0004: documents are pushed straight into the Azure AI Search index rather
than staged in Blob Storage and pulled by an indexer. The tenant applies a
`modify` policy that forces `publicNetworkAccess: Disabled` on every storage
account, which makes the blob data plane unreachable from a workstation.

The push model has a second, unrelated advantage worth naming on stage: there is
no indexer, so there is no window in which the knowledge base exists but is only
half populated. The document count is known synchronously.

Idempotent: re-running replaces documents whose content hash changed and leaves
the rest alone.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx
import yaml
from _common import (
    ROOT,
    ConfigError,
    console,
    fail,
    get_credential,
    load_config,
    ok,
    require_env,
    step,
)

CORPUS_DIR = ROOT / "corpus"
SEARCH_SCOPE = "https://search.azure.com/.default"
COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
BANNER_WINDOW = 400
BANNER_TEXT = "SYNTHETIC"
EMBEDDING_DIMENSIONS = 3072
EMBED_BATCH = 8


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_document(path: Path) -> dict:
    """Split YAML front matter from the body. Front matter is the retrieval contract."""
    raw = path.read_text(encoding="utf-8")

    if BANNER_TEXT not in raw[:BANNER_WINDOW]:
        fail(f"{path.name} is missing the SYNTHETIC banner in its first {BANNER_WINDOW} chars")

    if not raw.startswith("---"):
        fail(f"{path.name} has no YAML front matter")

    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front) or {}

    for field in ("doc_id", "title", "status", "effective_date"):
        if not meta.get(field):
            fail(f"{path.name} front matter is missing '{field}'")

    return {
        "doc_id": str(meta["doc_id"]),
        "title": str(meta["title"]),
        "doc_type": str(meta.get("doc_type", "unknown")),
        "status": str(meta["status"]),
        "effective_date": str(meta["effective_date"]),
        "supersedes": str(meta.get("supersedes") or ""),
        "contains_pii": bool(meta.get("contains_pii", False)),
        "owner": str(meta.get("owner", "")),
        "content": body.strip(),
        "content_hash": content_hash(raw),
    }


def build_index(name: str, foundry_endpoint: str, embedding_deployment: str) -> dict:
    """Index schema.

    `status` and `effective_date` are filterable and retrievable so the agent can
    see them and the recency guard has something to reason about. If they were
    index-only the stale-document story would not work.
    """
    return {
        "name": name,
        "fields": [
            {"name": "doc_id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "doc_type", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "effective_date", "type": "Edm.String", "filterable": True, "sortable": True},
            {"name": "supersedes", "type": "Edm.String", "filterable": True},
            {"name": "contains_pii", "type": "Edm.Boolean", "filterable": True},
            {"name": "owner", "type": "Edm.String", "filterable": True},
            {"name": "content_hash", "type": "Edm.String", "filterable": True},
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": EMBEDDING_DIMENSIONS,
                "vectorSearchProfile": "meridian-vector-profile",
            },
        ],
        "vectorSearch": {
            "algorithms": [{"name": "meridian-hnsw", "kind": "hnsw"}],
            "profiles": [
                {
                    "name": "meridian-vector-profile",
                    "algorithm": "meridian-hnsw",
                    "vectorizer": "meridian-vectorizer",
                }
            ],
            # Query-time vectorisation uses the Search service managed identity
            # against the Foundry account. No key anywhere in this path.
            "vectorizers": [
                {
                    "name": "meridian-vectorizer",
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": foundry_endpoint,
                        "deploymentId": embedding_deployment,
                        "modelName": "text-embedding-3-large",
                    },
                }
            ],
        },
        "semantic": {
            "configurations": [
                {
                    "name": "meridian-semantic",
                    "prioritizedFields": {
                        "titleField": {"fieldName": "title"},
                        "prioritizedContentFields": [{"fieldName": "content"}],
                    },
                }
            ]
        },
    }


def embed(
    foundry_endpoint: str, deployment: str, token: str, texts: list[str]
) -> list[list[float]]:
    """Embed via the Foundry deployment. Same model the vectorizer uses at query time."""
    url = f"{foundry_endpoint}/openai/deployments/{deployment}/embeddings"
    vectors: list[list[float]] = []

    with httpx.Client(timeout=180.0) as http:
        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start : start + EMBED_BATCH]
            response = http.post(
                url,
                params={"api-version": "2024-10-21"},
                headers={"Authorization": f"Bearer {token}"},
                json={"input": batch, "dimensions": EMBEDDING_DIMENSIONS},
            )
            if response.status_code != 200:
                fail(f"Embedding call failed → {response.status_code}: {response.text[:400]}")
            payload = response.json()
            vectors.extend(
                item["embedding"] for item in sorted(payload["data"], key=lambda d: d["index"])
            )

    if len(vectors) != len(texts):
        fail(f"Embedded {len(vectors)} of {len(texts)} documents")
    return vectors


def main() -> int:
    config = load_config()
    knowledge = config["knowledge"]
    models = config["models"]
    index_name = knowledge["index"]
    expected = int(knowledge["expected_document_count"])

    env = require_env("AZURE_SEARCH_ENDPOINT", "AZURE_AI_FOUNDRY_ENDPOINT")
    search_endpoint = env["AZURE_SEARCH_ENDPOINT"].rstrip("/")
    foundry_endpoint = env["AZURE_AI_FOUNDRY_ENDPOINT"].rstrip("/")
    api_version = config["project"]["api_version"]

    docs = sorted(CORPUS_DIR.glob("*.md"))
    if len(docs) != expected:
        fail(f"Expected {expected} corpus documents, found {len(docs)} in {CORPUS_DIR}")

    parsed = [parse_document(doc) for doc in docs]

    credential = get_credential()
    search_token = credential.get_token(SEARCH_SCOPE).token
    cognitive_token = credential.get_token(COGNITIVE_SCOPE).token

    headers = {
        "Authorization": f"Bearer {search_token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(base_url=search_endpoint, headers=headers, timeout=180.0) as http:
        step(f"Creating search index '{index_name}'")
        response = http.put(
            f"/indexes/{index_name}",
            params={"api-version": api_version},
            json=build_index(index_name, foundry_endpoint, models["embedding"]["deployment"]),
        )
        # 204 No Content is what Search returns when the PUT UPDATES an existing
        # index rather than creating one — it is success, not failure. Treating it
        # as an error makes the hook fail on every re-run but pass the first time,
        # which is the worst possible shape for a bug.
        if response.status_code not in (200, 201, 204):
            fail(f"Index create failed → {response.status_code}: {response.text[:600]}")
        ok(f"Index '{index_name}' created or updated")

        step(f"Embedding {len(parsed)} documents with {models['embedding']['deployment']}")
        vectors = embed(
            foundry_endpoint,
            models["embedding"]["deployment"],
            cognitive_token,
            [f"{doc['title']}\n\n{doc['content']}" for doc in parsed],
        )
        ok(f"Embedded {len(vectors)} documents")

        step(f"Pushing {len(parsed)} documents into '{index_name}'")
        payload = {
            "value": [
                {"@search.action": "mergeOrUpload", **doc, "content_vector": vector}
                for doc, vector in zip(parsed, vectors, strict=True)
            ]
        }
        response = http.post(
            f"/indexes/{index_name}/docs/index",
            params={"api-version": api_version},
            json=payload,
        )
        # 207 Multi-Status means some documents failed; the per-item check below
        # reports exactly which, so let it through to produce the better message.
        if response.status_code not in (200, 201, 207):
            fail(f"Document push failed → {response.status_code}: {response.text[:600]}")

        failures = [
            item for item in response.json().get("value", []) if not item.get("status", False)
        ]
        if failures:
            fail(f"{len(failures)} documents failed to index: {failures[:3]}")

        for doc in parsed:
            console.print(f"  [dim]indexed[/dim] {doc['doc_id']}")

        # Post-condition: the index holds exactly the corpus. A partially
        # populated index is the failure this whole script exists to prevent.
        step("Verifying document count")
        count = http.get(
            f"/indexes/{index_name}/docs/$count",
            params={"api-version": api_version},
            headers={**headers, "Accept": "text/plain"},
        )
        if count.status_code != 200:
            fail(f"Count failed → {count.status_code}: {count.text[:300]}")

        actual = int(count.text.strip().lstrip("\ufeff"))
        if actual != expected:
            fail(
                f"Index holds {actual} documents, expected {expected}. "
                "Refusing to continue — a partially populated index fails silently "
                "at demo time."
            )

    ok(f"Corpus indexed — {actual}/{expected} documents in '{index_name}'")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        fail(str(exc))
    except httpx.HTTPError as exc:
        fail(f"HTTP error talking to Azure AI Search: {exc}")
