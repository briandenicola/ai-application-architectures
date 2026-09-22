# ADR-0003: Ship two agent versions that differ only in instructions

- **Status:** Accepted
- **Date:** 2026-09-21
- **Amended:** 2026-09-28 — extended to the FinOps agent pair
- **Deciders:** @briandenicola

## Context

The demo has to make one argument convincingly: *evaluation catches things that
eyeballing the output does not.*

The tempting approach is a single well-built agent with good scores. It does not
work. A room full of green numbers proves nothing — the audience has no idea what
a bad score would have looked like, and a scorecard with nothing to compare it to
reads as marketing.

So: two agents, v1 fails, v2 passes. But that creates a credibility problem of its
own. If v2 also uses a better model, a lower temperature, and more retrieved
documents, a sceptical architect will — correctly — say the improvement proves
nothing about the prompt.

## Decision

v1 and v2 are identical except for two fields:

- `instructions`
- `knowledge.retrieval` (reranker threshold, max documents, citation inclusion)

Same model, same model version, same temperature (0.0), same `top_p`, same seed,
same knowledge base, same dataset, same evaluators, same thresholds.

`tests/test_agent_parity.py` enforces this. The test fails if any other field
diverges.

## Consequences

### Positive
- The on-screen diff is small enough to read aloud and is *honestly* the cause of
  the score change.
- Pre-empts the best objection in the room instead of absorbing it.
- Makes the actual lesson land: the delta is prompt engineering plus retrieval
  configuration, both of which are cheap, reviewable, and testable.
- Temperature 0.0 plus a fixed seed makes re-runs close to reproducible.

### Negative
- Constrains v2. Some improvements that would be sensible in production — a
  different model for the harder cases, a reranking step — are off the table
  because they would break parity.
- The parity test will fail on any legitimate future divergence, forcing a
  deliberate decision. That is the intent, but it is friction.

### Neutral
- v1 is not a straw man. It is three sentences with no guards, which is exactly
  what a first-draft agent looks like in practice. Its failures are the ordinary
  ones, not manufactured ones.

## Alternatives considered

| Option | Why not |
|--------|---------|
| One agent, show the scorecard | No baseline. Green numbers with no contrast persuade nobody. |
| Two agents with different models | Confounds the variable. Proves the model changed, not that the prompt mattered. |
| Live-edit one agent on stage | Attractive, but unrepeatable and slow, and a typo in front of a client is unrecoverable. Keep the live edit as an *optional* extension after the main arc has landed. |
| Make v1 obviously terrible | Loses the room. If v1 looks like nobody would ship it, the audience concludes the problem does not apply to them. |

## Amendment — the FinOps pair (2026-09-28)

The FinOps track adds `meridian-finops-v1` / `-v2`. The decision above applies
unchanged: same model deployment, same pinned model version, same index, same
dataset, same rubric, same thresholds. Enforced by
`tests/test_finops_agent_parity.py`.

Three differences in the *mechanics* are worth recording.

**The permitted-difference set is wider by one field.** The advisor pair may
differ in `instructions` and `knowledge.retrieval`. The FinOps pair may differ
in `name`, `description`, `instructions` and `knowledge`. `name` and
`description` are unavoidable — they are distinct published agents. `knowledge`
rather than `knowledge.retrieval` because this pair grounds through the
`azure_ai_search` tool (ADR-0005) rather than a Knowledge Base, so the whole
block differs in shape. The narrowing that matters is preserved separately:
`test_both_agents_use_the_same_index` and
`test_both_ground_against_the_finops_corpus_not_the_advisor_one` pin the index,
so a wider permitted set cannot hide a retrieval-target change.

**Reproducibility is pinned differently.** `gpt-5.5` is a reasoning model and
rejects `temperature`, `top_p` and `seed` outright, so the advisor pair's
"temperature 0.0 plus a fixed seed" lever does not exist. The pinned model
`version` is the only lever left, and `test_reproducibility_is_configured`
asserts both agents carry the same explicit version rather than floating on
`latest`. This is weaker than the advisor pair's guarantee, and saying so is
better than implying reproducibility that is not there.

**The two pairs must stay four distinct agents.**
`test_the_two_agent_pairs_are_distinct_agents` fails if a name collides. Both
sets publish into one project, and a collision would overwrite an agent in the
other track silently — a failure that would surface mid-demo, as a v2 agent
behaving like a v1.

### What the amendment does not change

v1 is still not a straw man. Read
[`v1-naive-finops.agent.yaml`](../../agents/v1-naive-finops.agent.yaml): every
instruction in it is one a reasonable platform team would write — *lead with the
number*, *use our current prices*, *don't bury it in caveats*, *you have the
owner registry, so help people find the right person*. Each is a plausible
productivity ask, and each removes a control.
`test_v1_actively_invites_the_planted_failures` fails if someone later softens
v1 into an agent nobody would have shipped.

### One consequence we did not anticipate

The parity contract holds the *configuration* constant, which is what makes the
prompt delta readable. It does not guarantee the delta is *visible in the
scores*. Live probing found that three of the six planted FinOps traps are
handled correctly by v1 anyway (`docs/finops-trap-probe.md`), so for those cases
the two agents score the same and the contrast the ADR exists to create simply
is not there.

Parity is necessary but not sufficient. A future agent pair needs both: hold
everything but the prompt constant, **and** verify the prompt delta actually
moves the score before writing the evaluation around it. The golden set was
reweighted toward synthesis cases on that evidence.

## Revisit when

The audience shifts to a purely technical one that wants to see the *process* of
iterating rather than the before-and-after. At that point a live-edit variant is
the better shape — but keep the parity contract for the recorded version.
