# Day 2 — From a demo to a control

What you say when someone asks "fine, but how does this live in our SDLC?"

## 1. The gate moves into CI

The evaluation already exits non-zero. Making it a merge requirement is
configuration, not engineering.

```yaml
# .github/workflows/agent-quality-gate.yml
name: Agent Quality Gate
on:
  pull_request:
    paths: ["src/evals/agents/**", "src/evals/datasets/**", "src/evals/evaluators/**"]

permissions:
  id-token: write        # OIDC — no stored credentials
  contents: read

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: pip install -e ".[dev]"
        working-directory: src/evals
      - run: python scripts/create_agents.py
        working-directory: src/evals
      - run: python scripts/run_eval.py --agent meridian-advisor-v2
        working-directory: src/evals      # non-zero exit fails the PR

      # Every agent set gets its own gate. A second track that is not gated is
      # a second track nobody is checking.
      - run: python scripts/create_agents.py --corpus finops
        working-directory: src/evals
      - run: python scripts/run_eval.py --corpus finops --agent meridian-finops-v2
        working-directory: src/evals
```

The point to make: **a prompt change is now a code change with a test.** Editing
an agent's instructions in a portal text box, with no review and no regression
check, is the actual risk in most organisations — not the model.

## 2. Continuous evaluation in production

Pre-deployment evaluation tells you the agent was good on 30 cases you thought of.
Continuous evaluation tells you what is happening on traffic you didn't.

- Sample production conversations at a fixed rate.
- Run groundedness and the compliance rubric against the sample.
- Emit to Application Insights; alert on a rolling-window drop.

This catches what a pre-deployment gate structurally cannot: corpus drift. Nobody
changed the prompt or the model — someone uploaded a document.

## 3. The dataset grows from incidents

The 30 advisor cases and 32 FinOps cases here were written in advance. In
production the dataset should be fed by reality:

- Every escalation becomes a case.
- Every compliance finding becomes a case.
- Every "the agent told me something odd" becomes a case.

A regression suite assembled from real failures is worth more than a larger one
assembled from imagination, and it cannot be gamed by tuning against it — the
cases arrive after the tuning.

**And test the cases you invent before you trust them.** Both FinOps agents
were probed against the live deployment before the golden set was written, and
three of the six planted traps turned out to be handled by the model unaided
(`docs/finops-trap-probe.md`). Had that check been skipped, half the suite
would have consisted of cases that pass for both a guarded and an unguarded
agent — a suite that looks thorough, runs green, and discriminates nothing.

The generalisation: **a case that both versions pass is not a test, it is
decoration.** When a dataset is written from imagination, measure which cases
actually separate the two before shipping it as a control.

## 3b. When a second domain arrives

Adding the FinOps track surfaced two things worth expecting.

**The guards do not transfer; the machinery does.** Retrieval, grounding,
exit-code semantics, the seeding scripts and the gate were reused unchanged via
a `--corpus` flag. The *rules* inverted: the advisor rule "prefer the newest
document" is the FinOps bug. Budget for writing new domain rules, not new
plumbing — and resist consolidating two rubrics that look similar.

**Answer keys drift faster than corpora.** The FinOps golden set is generated
from the same fact table as its corpus, so a change to one moves both. A
hand-written answer key against a changing corpus decays silently and marks
correct answers wrong, which presents as a model regression and gets debugged
as one.

## 4. Production security posture

This demo is deliberately public-endpoint. A real deployment adds:

| Control | Why |
|---------|-----|
| Private endpoints on Foundry and Search | Remove public data-plane exposure |
| Blob-backed knowledge source + shared private link | The production ingestion pattern this demo trades away — see ADR-0004 |
| VNet integration + DNS zones | Traffic stays on the backbone |
| Customer-managed keys | Where the data classification requires it |
| **Document-level ACLs / permission-aware retrieval** | The real answer to T2 — a prompt instruction is not access control |
| Diagnostic settings to a retained workspace | Evidence for audit |
| Azure Policy | Prevent drift on the above |

The Terraform modules under `infrastructure/` in this repository already
demonstrate several of these patterns against Foundry, including managed-VNet and
private-endpoint variants.

## 5. Governance artifacts

The part that actually lands with a risk function. Three files, all reviewable in
a pull request:

| Artifact | Owner |
|----------|-------|
| `datasets/meridian-golden-v1.jsonl` | Business + Compliance define the cases |
| `evaluators/compliance_safe_answer.yaml` | Compliance owns the rubric |
| `evals.config.yaml` thresholds | Agreed jointly, changed by PR |

> The conversation shifts from "do you trust the agent" to "do you agree with the
> threshold". The second question has an owner, an audit trail, and a change
> process. The first one never did.

## 6. What this pattern does not solve

Be straight about this; it buys credibility for everything else.

- It does not make the model deterministic.
- It does not prove the absence of a failure mode you did not think to test.
- It does not replace human review for high-consequence decisions.
- It does not fix a document estate that nobody governs — it only makes the
  consequences visible sooner.
