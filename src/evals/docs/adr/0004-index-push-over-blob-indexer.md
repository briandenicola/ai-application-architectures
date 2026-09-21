# ADR-0004: Push the corpus into the search index instead of staging it in Blob Storage

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** @briandenicola
- **Supersedes part of:** ADR-0002 (the knowledge source kind, not the REST decision)

## Context

The original design staged the 12 synthetic documents in Azure Blob Storage and
pointed a Foundry IQ knowledge source (`kind: azureBlob`) at the container. An
indexer pulled and chunked them.

That design failed on first deployment, and not for a reason we could fix in our
own code. The tenant applies a governance policy — `MCAPSGovDeployPolicies`,
containing `StorageAccount_PublicNetwork_Modify` — with a **`modify`** effect
that forces `publicNetworkAccess: Disabled` on every storage account at creation.
Our Bicep requested `Enabled`; policy silently overrode it.

The consequence: the blob data plane is unreachable from a workstation. The
corpus upload fails with `AuthorizationFailure`, which is a misleading error —
RBAC was correct all along.

Restoring blob access would have meant either overriding a corporate policy, or
adding a private endpoint plus a shared private link from Search to storage, plus
DNS and an approval step. Both are bad trades for a 45-minute demo that is
supposed to stand up in one command.

## Decision

Delete Blob Storage from the architecture. `scripts/index_corpus.py` creates the
Azure AI Search index, embeds each document with the Foundry
`text-embedding-3-large` deployment, and pushes the documents directly via the
Search data plane. The knowledge source becomes `kind: searchIndex` pointing at
that index.

## Consequences

### Positive
- **No indexer, therefore no indexing window.** The document count is known
  synchronously at push time. The "half-populated knowledge base" failure — the
  one `setup_knowledge.py` exists to prevent — is now structurally impossible
  rather than merely detected.
- Fewer resources: no storage account, no container, and three fewer RBAC
  assignments (10 → 7).
- Front matter becomes first-class index fields. `status` and `effective_date`
  are filterable and retrievable, which makes the stale-document trap legible in
  the portal instead of buried in chunk text.
- Policy-compliant. Nothing is circumvented.
- Faster: no indexer schedule to wait on.

### Negative
- **The demo no longer shows "Foundry IQ over your document estate in blob
  storage"**, which is the shape most clients will actually have. The narrative
  shifts from "point it at your documents" to "index your documents". Worth
  saying out loud, along with `docs/day-2.md`, where the blob + private endpoint
  pattern is the production answer.
- Chunking is ours, not the indexer's. With 12 short documents, one document per
  index record is fine; at real scale it would not be.
- Embeddings are computed at push time, so re-indexing costs model calls.

### Neutral
- Query-time vectorisation still uses an `azureOpenAI` vectorizer on the index,
  authenticated by the Search service managed identity. The keyless
  non-negotiable is untouched — nothing in this path uses a key.

## Discovered while implementing

Documented here because the API surface is new and the documentation lags.
Verified against the live service at `2026-04-01` on 2026-09-21:

| Expectation | Reality |
|---|---|
| Knowledge base accepts `retrievalInstructions` | **It does not.** The type behind `/knowledgeBases` exposes only `name`, `description`, `knowledgeSources`, `models`, `encryptionKey`. |
| `rerankerThreshold` is knowledge-base configuration | It is a **retrieve-time** parameter, passed in `knowledgeSourceParams`. |
| Retrieve takes `messages` | It takes `intents`, e.g. `{"search": "...", "type": "semantic"}`. `messages` was a preview-era shape. |
| Retrieve path is `/knowledgeBases/{name}/retrieve` | The service expects the OData form `/knowledgebases('{name}')/retrieve`. |

**The consequence that matters:** the recency instruction previously lived in
both the knowledge base *and* the v2 prompt — deliberate defence in depth. The
knowledge base half is not expressible at this API version, so **it now lives
only in the v2 prompt**. That is a genuine reduction in robustness, and it is
recorded in `docs/demo-traps.md` rather than quietly dropped. The canary in
`setup_knowledge.py` is now the only automated protection for the ranking.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Re-enable public network access on the storage account | Deliberately contradicts a corporate policy, and the `modify` effect would revert it on the next write. |
| Private endpoint + shared private link | Correct for production, wrong for a one-command demo. It is in `docs/day-2.md`. |
| Deploy in a subscription without the policy | Makes the demo dependent on an unusual subscription. It would fail at the first client who has the same governance — which is most of them. |

## Revisit when

The demo is delivered in a subscription where blob public access is permitted
**and** the audience specifically wants to see indexer-based ingestion. The
`azureBlob` knowledge source kind still exists and the payload is recorded in
this repository's git history.
