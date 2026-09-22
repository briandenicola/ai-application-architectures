# ADR-0007: Generate the FinOps corpus from a fact table instead of hand-authoring it

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** @briandenicola

## Context

The second demo dataset covers agentic token usage and cost across eight
business units, five models, and six months, under two rate cards. That is
roughly 240 usage rows, and the rows are not independent: they roll up by
business unit, by model, and by month, and the same figures reappear in a
half-year summary, an incident review, a forecast, and a budget-variance table.

The evaluation this corpus exists to support makes one specific claim — that
an agent which gets the arithmetic wrong, prices a period against the wrong
rate card, or reports metered cost where billed cost was asked for is
*demonstrably* wrong, not arguably wrong. That claim survives a skeptical
audience only if the documents themselves reconcile exactly.

Hand-authoring was the default, by analogy with `corpus/`, where twelve
documents were written by hand and it worked fine. It does not scale here. A
single edited figure has to be chased through four other documents, and the
first time it is missed, the corpus contains a genuine contradiction. At that
point every failed evaluation case needs adjudicating by hand to decide whether
the agent was wrong or the corpus was — which is precisely the work the demo
claims to eliminate.

## Decision

The FinOps corpus is **generated**. `scripts/finops_data.py` holds the fact
table and the pricing rules; `scripts/generate_finops_corpus.py` renders all
nineteen documents from it. The rendered markdown is committed.

Three properties make this safe:

1. **Deterministic.** Volumes derive from a SHA-256 of the (business unit,
   month) pair rather than a seeded PRNG, so output is byte-identical across
   machines and interpreters. A corpus that drifts between regenerations cannot
   be reviewed in a diff.
2. **Committed, with a freshness check.** The markdown is in the repository so
   a reviewer can read it in a PR without running anything.
   `generate_finops_corpus.py --check` — run as a unit test — fails if the
   committed copy has drifted from the generator.
3. **Verified independently.** `tests/test_finops_corpus.py` parses the
   *rendered documents* and re-adds every total. It does not ask the generator
   whether the generator is correct.

Point 3 is not theoretical. The first version of the repricing test recomputed
costs with the same `rate_card_for()` helper it was meant to validate. A tamper
test that pinned every month to the wrong rate card regenerated the corpus at
the wrong prices — and the test agreed with the bug and passed. The test now
reads the rates out of the rate-card document the statement names. See
`docs/tamper-log.md` § T9.1.

## Consequences

**Good.** Adding a month, a business unit, or a model is a constants change.
Every dependent total updates and the tests prove they still tie out. The
arithmetic in the corpus is trustworthy enough to grade an agent against.

**Bad.** The corpus cannot be edited directly — an edit is silently reverted by
the next regeneration, and `--check` will fail in the meantime. Prose changes
mean editing a Python string, which is worse than editing markdown. Reviewing a
prose change means reading a diff of both the template and the output.

**Deliberately not done.** The advisor corpus in `corpus/` was *not* migrated to
this approach. Twelve hand-written documents with no cross-document arithmetic
do not have this problem, and rewriting them would add risk to a demo that
works for no benefit. Generation is the right answer for arithmetic-heavy
corpora specifically — not a new house style.
