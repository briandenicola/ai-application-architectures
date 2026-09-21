#!/usr/bin/env python3
"""Create the Foundry IQ knowledge source and knowledge base over the corpus.

ADR-0002: implemented against the Azure AI Search REST API rather than Bicep,
because knowledge sources and knowledge bases are not expressible in ARM at the
pinned API version. Revisit when they are.

ADR-0004: the knowledge source is `kind: searchIndex` over an index populated by
scripts/index_corpus.py, not `kind: azureBlob`.

This script is the single most important guard in the setup path. A half-indexed
knowledge base produces an agent that answers confidently from three of twelve
documents, which looks fine in the playground and falls apart on stage. So the
script refuses to exit 0 until two post-conditions hold:

  1. the index holds exactly the expected document count
  2. a canary query ranks the CURRENT fee schedule above the SUPERSEDED one

If either fails, azd up fails loudly and early.
"""

from __future__ import annotations

import os
import sys

import httpx
from _common import (
    ConfigError,
    console,
    fail,
    get_credential,
    load_config,
    ok,
    require_env,
    step,
    warn,
)

SEARCH_SCOPE = "https://search.azure.com/.default"
API_VERSION = "2026-04-01"

CANARY_QUERY = "What is the advisory fee on a $2.5M managed account?"
CANARY_EXPECTED = "meridian-fee-schedule-2026"
CANARY_FORBIDDEN = "meridian-fee-schedule-2025"


def client(endpoint: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=endpoint,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"api-version": API_VERSION},
        timeout=120.0,
    )


def put(http: httpx.Client, path: str, body: dict) -> dict:
    """Idempotent create-or-update."""
    response = http.put(path, json=body)
    if response.status_code not in (200, 201, 204):
        fail(f"PUT {path} → {response.status_code}: {response.text[:500]}")
    return response.json() if response.content else {}


def build_knowledge_source(config: dict, env: dict) -> dict:
    knowledge = config["knowledge"]
    return {
        "name": knowledge["knowledge_source"],
        # kind=searchIndex, not azureBlob: the corpus is pushed straight into the
        # index by index_corpus.py. Verified against the live API — the service
        # requires searchIndexParameters and the target index to already exist.
        "kind": "searchIndex",
        "description": "Meridian Wealth Partners document estate (synthetic).",
        "searchIndexParameters": {
            "searchIndexName": knowledge["index"],
        },
    }


def build_knowledge_base(config: dict, env: dict) -> dict:
    """Knowledge base payload.

    Deliberately minimal, because that is all the API accepts. Verified against
    the live service at 2026-04-01: the type behind /knowledgeBases exposes only
    name, description, knowledgeSources, models and encryptionKey.

    Notably absent: `retrievalInstructions` and `rerankerThreshold`. The recency
    guidance that used to live here now exists ONLY in the v2 agent prompt — see
    ADR-0004. That is a real reduction in defence in depth and is called out in
    docs/demo-traps.md rather than quietly dropped.
    """
    knowledge = config["knowledge"]
    models = config["models"]
    return {
        "name": knowledge["knowledge_base"],
        "description": "Grounding for the Meridian advisor agent.",
        "knowledgeSources": [{"name": knowledge["knowledge_source"]}],
        "models": [
            {
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": env["AZURE_AI_FOUNDRY_ENDPOINT"],
                    "deploymentId": models["judge"]["deployment"],
                    "modelName": models["judge"]["deployment"],
                },
            }
        ],
    }


def verify_index_population(http: httpx.Client, index_name: str, expected: int) -> None:
    """Post-condition 1: the index holds exactly the corpus.

    With the push model there is no indexer to wait on, so this is a synchronous
    check rather than a poll. It stays here as well as in index_corpus.py because
    this script is the one people re-run before a meeting.
    """
    step(f"Verifying '{index_name}' holds {expected} documents")
    response = http.get(f"/indexes/{index_name}/docs/$count", headers={"Accept": "text/plain"})
    if response.status_code != 200:
        fail(f"Count failed → {response.status_code}: {response.text[:300]}")

    actual = int(response.text.strip().lstrip("\ufeff"))
    if actual != expected:
        fail(
            f"Index holds {actual} documents, expected {expected}. "
            "Run scripts/index_corpus.py — a partially populated index fails "
            "silently at demo time."
        )
    ok(f"Index holds {actual}/{expected} documents")


def canary_retrieval(http: httpx.Client, config: dict) -> None:
    """Post-condition 2: the current fee schedule must outrank the superseded one.

    This is the assertion that protects the centrepiece of the demo. If retrieval
    prefers the 2025 schedule, the stale-doc narrative collapses — and worse, v2
    would fail its own gate for reasons that have nothing to do with the prompt.
    """
    step("Canary retrieval: current fee schedule must outrank the superseded one")

    knowledge = config["knowledge"]
    # Request shape verified against the live API at 2026-04-01. `intents` with
    # type=semantic skips model query planning, which keeps the canary cheap and
    # deterministic. rerankerThreshold is a RETRIEVE-time parameter — it is not
    # a property of the knowledge base, despite what you might expect.
    response = http.post(
        f"/knowledgebases('{knowledge['knowledge_base']}')/retrieve",
        json={
            "intents": [{"search": CANARY_QUERY, "type": "semantic"}],
            "includeActivity": True,
            "maxRuntimeInSeconds": 60,
            "knowledgeSourceParams": [
                {
                    "kind": "searchIndex",
                    "knowledgeSourceName": knowledge["knowledge_source"],
                    "includeReferences": True,
                    "includeReferenceSourceData": True,
                    "rerankerThreshold": knowledge["reranker_threshold"],
                }
            ],
        },
    )
    if response.status_code != 200:
        fail(f"Canary retrieval failed → {response.status_code}: {response.text[:500]}")

    payload = response.json()
    refs = payload.get("references", []) or []
    ordered = [
        str(ref.get("docKey") or (ref.get("sourceData") or {}).get("doc_id") or "") for ref in refs
    ]
    ranked = [doc for doc in ordered if doc]

    console.print(f"  [dim]ranking: {ranked[:5]}[/dim]")

    if CANARY_EXPECTED not in " ".join(ranked):
        fail(
            f"Canary failed: '{CANARY_EXPECTED}' not retrieved for the fee query. "
            "Check that index_corpus.py ran and lower the reranker threshold."
        )

    def position(needle: str) -> int:
        for index, doc in enumerate(ranked):
            if needle in doc:
                return index
        return len(ranked) + 1

    if position(CANARY_EXPECTED) > position(CANARY_FORBIDDEN):
        fail(
            f"Canary failed: superseded '{CANARY_FORBIDDEN}' outranks current "
            f"'{CANARY_EXPECTED}'. Tune the reranker threshold or the v2 recency "
            "guard before demoing — the stale-document story depends on this."
        )

    ok("Canary passed: current schedule ranks above the superseded one")


def main() -> int:
    config = load_config()
    env = require_env(
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_AI_FOUNDRY_NAME",
    )
    env["AZURE_AI_FOUNDRY_ENDPOINT"] = os.environ.get(
        "AZURE_AI_FOUNDRY_ENDPOINT",
        f"https://{env['AZURE_AI_FOUNDRY_NAME']}.cognitiveservices.azure.com",
    )

    knowledge = config["knowledge"]
    token = get_credential().get_token(SEARCH_SCOPE).token

    with client(env["AZURE_SEARCH_ENDPOINT"], token) as http:
        # Order matters: the service rejects a searchIndex knowledge source whose
        # target index does not exist, so the index must be populated first.
        verify_index_population(
            http,
            knowledge["index"],
            int(knowledge["expected_document_count"]),
        )

        step(f"Creating knowledge source '{knowledge['knowledge_source']}'")
        put(
            http,
            f"/knowledgeSources/{knowledge['knowledge_source']}",
            build_knowledge_source(config, env),
        )
        ok("Knowledge source created or updated")

        step(f"Creating knowledge base '{knowledge['knowledge_base']}'")
        put(
            http,
            f"/knowledgeBases/{knowledge['knowledge_base']}",
            build_knowledge_base(config, env),
        )
        ok("Knowledge base created or updated")

        canary_retrieval(http, config)

    ok("Foundry IQ knowledge base is healthy and ready to demo")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        fail(str(exc))
    except httpx.HTTPError as exc:
        warn("If this is a 403, RBAC propagation can lag provisioning by a minute or two.")
        fail(f"HTTP error talking to Azure AI Search: {exc}")
