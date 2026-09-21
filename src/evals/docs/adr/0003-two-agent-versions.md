# ADR-0003: Ship two agent versions that differ only in instructions

- **Status:** Accepted
- **Date:** 2026-09-21
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

## Revisit when

The audience shifts to a purely technical one that wants to see the *process* of
iterating rather than the before-and-after. At that point a live-edit variant is
the better shape — but keep the parity contract for the recorded version.
