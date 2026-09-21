# ADR-0005: Ground prompt agents through an Azure AI Search connection

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** @briandenicola
- **Builds on:** ADR-0004 (corpus pushed into the index)

## Context

The demo was specified around **Foundry IQ**: a knowledge base over the document
estate, attached to two prompt agents. `setup_knowledge.py` builds that knowledge
base and it works — the canary proves the 2026 fee schedule outranks the 2025 one
through the `/retrieve` endpoint.

What does not exist is a way to attach it to a prompt agent at this API version.
Verified against the live service on 2026-09-21:

- `azure-ai-projects` 2.7.0 models no knowledge-base tool. `ToolType` has 34
  members; none of them is a knowledge base.
- The project data plane has no knowledge base endpoint. `/knowledgeBases`,
  `/knowledgebases` and `/knowledgeSources` all return 404. `/indexes` returns
  200.
- Prompt agents ground through the `azure_ai_search` tool, which resolves an
  index through a **project connection**.

## Decision

Agents ground via the `azure_ai_search` tool against the same `meridian-docs`
index the knowledge base uses. A `CognitiveSearch` project connection is created
in Bicep with `authType: ProjectManagedIdentity`.

v1 and v2 differ in retrieval as well as prompt, which was always the design:

| | v1 (naive) | v2 (hardened) |
|---|---|---|
| `query_type` | `simple` (keyword only) | `vector_semantic_hybrid` |
| `top_k` | 3 | 5 |

The knowledge base is retained. It is the Foundry IQ artifact, it is visible in
the portal, and the canary exercises it on every deploy. It is honest to say on
stage that retrieval configuration and agent grounding are separate concerns
today.

## The finding that matters most

**The agent API does not validate tools at creation time.**

A `POST` to `/agents/{name}/versions` with a tool of type `totally_bogus_xyz`
returned `200` and a live agent. So did a `knowledge_base` tool that the service
has no implementation for. Tools are resolved when the agent runs, not when it
is created.

The practical consequence for anyone demoing this: **a successful deploy tells
you nothing about whether your agent works.** A typo in a tool block, a missing
connection, a deleted index, or a missing role assignment all produce a green
`azd up` and an agent that fails on its first question in front of the client.

`create_agents.py` therefore ends with a **smoke test** that asks each agent a
real grounded question and fails the deploy if it does not answer. That check
caught three genuine bugs within minutes of being written:

1. `model` must equal the agent's own deployment; passing the agent name is
   rejected.
2. `gpt-5.5` is a reasoning model and rejects `temperature`, `top_p` and `seed`
   outright. The agent definitions had all three.
3. The grounding identity had no access to the search index.

Every one of those would have surfaced on stage.

## Identity — the expensive part

The `azure_ai_search` tool authenticates as the **Foundry account**
system-assigned identity. Not the project identity, which is the intuitive guess
and is what the original Bicep granted. Microsoft documents two roles on the
account identity, both required:

- `Search Index Data Contributor`
- `Search Service Contributor`

`Search Index Data Reader` is **not** sufficient, despite the agent only ever
reading. That is a genuine least-privilege wart and it is called out in
`docs/threat-model.md` rather than glossed over.

Two things made this far harder to diagnose than it should have been:

- The error is `Access denied. Check your permissions or managed identity access
  to the search service.` It names no identity, no role and no resource. The
  same string appears whether the problem is the account identity, the project
  identity, or propagation.
- **Propagation to the Search data plane took roughly 5 minutes.** Long enough
  that a correct fix looks like a failed one, which invites changing something
  that was already right.

`smoke_test()` retries for up to 10 minutes on this specific failure for exactly
that reason.

### Known debt

While diagnosing, roles were granted to the project identity and the per-agent
identities as well. The agent-identity grants were removed. The project identity
retains `Search Service Contributor` and `Search Index Data Contributor` in the
live environment; the Bicep does **not** grant these, so a clean deploy will not
have them. The minimal working set has not been re-verified from a clean
subscription — that is a day-2 task, not a claim this repository should make.

## Consequences

### Positive
- The grounding path is the documented, SDK-modelled one.
- The smoke test converts a silent, on-stage failure into a loud deploy failure.
  This is now one of the better teaching moments in the demo.
- v1 vs v2 differs in retrieval strategy as well as prompt, which is a more
  realistic comparison.

### Negative
- The Foundry IQ knowledge base is no longer in the agent's request path. The
  narrative has to be precise about that.
- `Search Index Data Contributor` is more privilege than the workload needs.
- Agent identity is per agent and created on demand, so nothing about it can be
  pre-provisioned declaratively.

### Neutral
- Reproducibility for the agent now rests on the pinned model version and a fixed
  prompt rather than `temperature: 0.0`. The judge model (`gpt-4.1-mini`, see
  ADR-0006) **does** accept `temperature: 0.0` and a `seed`, so scoring
  stability — the part that actually decides pass or fail — is preserved.

## Revisit when

A knowledge-base tool type appears in `ToolType`, or the project data plane grows
a knowledge base endpoint. At that point the agents should bind the knowledge
base directly and this ADR should be superseded.
