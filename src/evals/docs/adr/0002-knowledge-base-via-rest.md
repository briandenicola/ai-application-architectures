# ADR-0002: Create the Foundry IQ knowledge base via REST in a post-provision hook

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** @briandenicola

## Context

The demo needs a Foundry IQ **knowledge source** (pointing at the search index)
and a **knowledge base** (the retrieval surface the agents call), at API version
`2026-04-01`.

Everything else in the stack — Foundry account, project, model deployments,
Search service, RBAC — is declarative Bicep. It would be cleaner if the
knowledge base were too.

The constraint: knowledge sources and knowledge bases are **data-plane** objects
on the Foundry project. They are not ARM resource types, so Bicep cannot create
them. This is the same reason a Search index cannot be declared in Bicep.

There is a second, sharper reason. Creating the objects is not the hard part;
**confirming they actually work** is. A knowledge base that exists but has indexed
zero documents looks perfectly healthy in the portal and destroys the demo. No
declarative resource model asserts "and the ranking is correct."

## Decision

Create both objects via REST in `scripts/setup_knowledge.py`, invoked by the
`postprovision` hook. The script is idempotent and **refuses to exit 0** unless
both post-conditions hold:

1. Indexed document count equals the corpus count (12).
2. A canary retrieval ranks `meridian-fee-schedule-2026` above
   `meridian-fee-schedule-2025`.

> Amended by ADR-0004. The original first post-condition was "indexer status is
> `success`"; there is no longer an indexer, so the count is checked
> synchronously instead of polled.

## Consequences

### Positive
- The post-conditions are the real value. The failure they prevent — a
  half-populated knowledge base — is the single most likely cause of a demo going
  wrong, and it is silent.
- `azd up` remains one command; the hook is invisible when it works.
- Re-runnable before a meeting as a health check (see the pre-flight checklist).
- The canary doubles as a regression test on retrieval configuration.

### Negative
- Imperative code in an otherwise declarative stack.
- The REST payload shapes are pinned to API `2026-04-01` and will need review
  when that version moves.
- `azd down` does not remove these objects; they disappear with the account.

### Neutral
- The REST calls are keyless, using the same `DefaultAzureCredential` chain as
  everything else.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Wait for Bicep support | Not available at `2026-04-01`. Blocking on it blocks the demo. |
| `deploymentScripts` resource in Bicep | Adds a container instance and a managed identity purely to run a Python script. More infrastructure, harder to debug, and the logs are worse. |
| Manual portal setup | Fails "reproducible" and "one command". Also the most likely to be half-done. |
| Create the objects but skip verification | This is the default failure. The objects exist, the index is empty or half-populated, retrieval returns nothing, and the first live query is where you find out. |

## Revisit when

Knowledge sources and knowledge bases become ARM resource types. Even then, keep
the verification step — declaring a resource has never been the same as
confirming it behaves.
