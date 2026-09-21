# Architecture

## Overview

```mermaid
flowchart TB
    subgraph rg["Resource Group (azd-managed, disposable)"]
        subgraph estate["Document estate"]
            corpus[("corpus/*.md<br/>12 synthetic documents<br/>YAML front matter")]
        end

        subgraph iq["Foundry IQ"]
            ks["Knowledge Source<br/>searchIndex<br/>see ADR-0004"]
            kb["Knowledge Base<br/>agentic retrieval<br/>query planning, rerank, cite"]
            search["Azure AI Search<br/>semantic ranker"]
        end

        subgraph foundry["Microsoft Foundry"]
            v1["Prompt Agent v1<br/>naive"]
            v2["Prompt Agent v2<br/>hardened"]
            models["Model deployments<br/>gpt-5.5 · gpt-5.4-mini · embedding-3-large"]
            evals["Evaluations<br/>5 built-in + 1 custom rubric"]
        end

        obs["Log Analytics<br/>Application Insights"]
    end

    dataset[("Golden dataset<br/>30 tagged cases")]
    gate{{"Quality gate<br/>exit 0 or 1"}}

    corpus -->|index_corpus.py<br/>embed + push| search
    search --> ks --> kb
    kb --> v1
    kb --> v2
    models -.-> v1
    models -.-> v2
    models -.-> evals
    v1 --> evals
    v2 --> evals
    dataset --> evals
    evals --> gate
    evals -.traces.-> obs

    classDef fail stroke:#c0392b,stroke-width:2px
    classDef pass stroke:#27ae60,stroke-width:2px
    class v1 fail
    class v2 pass
```

## The retrieval path

1. A question arrives at the prompt agent.
2. The agent calls its knowledge base tool.
3. Foundry IQ decomposes the question into subqueries and plans retrieval.
4. Azure AI Search executes them against the vectorized corpus, applies the
   semantic reranker, and drops results below the reranker threshold.
5. Results are merged, reranked, and returned with source references.
6. The agent composes an answer. Under v2, every claim carries a citation.

Recency preference — prefer `status: current` and later `effective_date` — was
designed to live in both the knowledge base and v2's prompt, as defence in depth.
The `2026-04-01` API has no `retrievalInstructions` property, so **it now lives
only in v2's prompt** (ADR-0004). One layer, not two. The canary assertion in
`setup_knowledge.py` is what stops that single layer failing silently.

Because `index_corpus.py` pushes documents directly, `status` and
`effective_date` are real index fields rather than text buried in a chunk — which
is what makes the stale-document trap visible in the portal.

## The evaluation path

```mermaid
sequenceDiagram
    participant D as Golden dataset (30 cases)
    participant A as Agent under test
    participant KB as Foundry IQ
    participant J as Judge model (gpt-5.4-mini)
    participant G as Quality gate

    loop each case
        D->>A: query
        A->>KB: retrieve
        KB-->>A: context + citations
        A-->>J: response + context + citations + case metadata
        J-->>J: 5 built-in evaluators
        J-->>J: compliance_safe_answer rubric
        J-->>G: scores + per-case reasons
    end
    G->>G: compare means to thresholds
    G-->>D: verdict + exit code (0 pass / 1 fail)
```

The agent and the judge use **different** models. A model grading its own output
is a weaker signal, and it is the first thing a sceptical architect will probe.

## Trust boundaries and identity

| Flow | Principal | Mechanism |
|------|-----------|-----------|
| Search vectorizer → embedding model | Search system-assigned MI | `Cognitive Services User` |
| Agent `azure_ai_search` tool → index | Foundry **account** system-assigned MI | `Search Index Data Contributor` + `Search Service Contributor` |
| Knowledge base retrieval → index | Project system-assigned MI | `Search Index Data Reader` |
| Foundry project → App Insights | Project system-assigned MI | `Monitoring Metrics Publisher` |
| Presenter → everything | Entra user token | Resource-scoped data-plane roles |

There are no keys anywhere in this system. `disableLocalAuth` is true on the
Search service, the Foundry account and Application Insights, so the keyless
claim is enforced by configuration rather than by convention. Nine role
assignments, each scoped to one resource.

Two of them are broader than the workload needs: the `azure_ai_search` tool only
reads, but Microsoft requires `Search Index Data Contributor` on the account
identity and `Search Index Data Reader` is rejected. ADR-0005 records the
evidence; `docs/threat-model.md` carries the residual risk rather than hiding
it.

## What is deliberately absent

- **Private endpoints and VNet integration.** A real FSI deployment would have
  them. They add deployment time and cost without changing anything this demo is
  about. `docs/day-2.md` covers the production posture.
- **Multi-agent orchestration.** Prompt agents are legible in the portal. A
  workflow of agents would move attention away from the evaluation.
- **A custom UI.** The portal and the terminal are the interface.

## Cost shape

| Resource | Driver |
|----------|--------|
| Azure AI Search (Basic) | Fixed hourly — the floor of the environment cost |
| Model deployments | Pay per token; idle deployments cost nothing |
| Log Analytics | Negligible at demo volume, 30-day retention |

Per-evaluation cost is 30 cases × 6 evaluators against a small judge model, plus
30 agent completions. Measured figures go in `README.md` (task T10.2).

The environment is designed to be created before an engagement and destroyed
after. `azd down --purge` plus `scripts/verify_teardown.py` makes that safe to do
routinely.
