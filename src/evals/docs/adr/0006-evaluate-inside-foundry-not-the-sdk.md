# ADR-0006: Evaluate inside Foundry, not in a local SDK

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** @briandenicola
- **Supersedes the evaluation approach in:** ADR-0003 (two agent versions — the
  comparison itself is unchanged, only where it executes)

## Context

The original harness scored agents locally with `azure-ai-evaluation`. It worked:
it called each agent, scraped the retrieved context out of the tool output, ran
the built-in evaluators in-process and printed a scorecard.

It also made the demo's central claim unprovable. The Foundry portal's
Evaluations tab was **empty**, because nothing was ever sent to the service. The
scorecard existed only in a terminal, and the product being demonstrated had no
record that any evaluation had happened.

For a demo whose entire purpose is to show that *Foundry* governs agent quality,
that is fatal. A client asking "so where does this live?" would get the honest
answer "on my laptop."

## Decision

**All evaluation executes server-side in Foundry. The repository contains no
evaluation SDK.**

Runs are created over the REST data plane with an **agent target**:

```json
"target": { "type": "azure_ai_agent", "name": "meridian-advisor-v1", "version": "3" }
```

Foundry calls the published prompt agent itself, runs every evaluator against
the result, and stores the run. The terminal scorecard and the portal scorecard
are now the *same artifact* rather than two things that happen to agree.

`azd` seeds the evaluator catalog entry and the golden dataset; the presenter
creates and runs the evaluation from the portal, or runs `run_eval.py` for the
CI gate. Both paths hit the same service and produce the same run.

## What the live service actually does

The REST specs are wrong or silent in several places that cost real time. All of
the following were verified by probing the deployed service, not by reading
documentation.

**Custom evaluator bodies are flat.** The spec's nested
`{"type": "custom", "evaluator": {...}}` shape is rejected with
`The Definition field is required.` — an error that points at exactly the field
you did supply. The service wants `display_name` / `evaluator_type` /
`categories` / `definition` at the top level.

**Built-ins take `deployment_name`; the custom rubric takes `model`.** Swapping
them yields an unhelpful 400.

**Two paging dialects coexist.** `/evaluators` and `/datasets` page Azure-style
(`value` + `nextLink`); `/agents` and `/openai/*` page OpenAI-style (`data` +
`has_more` + cursor). Handling only one returns an empty list, which is
indistinguishable from "the resource does not exist" — the failure mode is a
wrong answer, not an error.

**Continuation links must be used verbatim.** `httpx` *replaces* a URL's query
string when `params` is passed, including `params={}`. Passing anything
alongside a `nextLink` silently strips its `api-version` and cursor.

**Versioning is inconsistent.** `/openai/v1/*` routes are path-versioned and
reject an `api-version` parameter; `/datasets`, `/evaluators` and `/agents`
require `?api-version=2025-11-15-preview`. `/evaluators` additionally requires
the header `Foundry-Features: Evaluations=V1Preview`.

**The native `evaluations/runs:run` surface is `@removed(Versions.v1)`.** It is
present in the spec and must not be used.

## The three findings that changed the design

### Evaluators never see tool outputs

Foundry exposes the agent's `output_text` and its message/tool-call trace to
evaluators. It does **not** expose tool *results*. You can see that the agent
searched; you cannot see what came back.

This breaks textbook groundedness and retrieval against an agent target, because
there is no retrieved context to ground against. Two consequences:

- **Groundedness is scored against the golden set's `ground_truth`.** This
  answers "is the answer faithful to the correct source material?" rather than
  "is it faithful to what this run retrieved?" That is a weaker claim and the
  narrative must say so.
- **`retrieval` is dropped entirely.** Scored this way it would grade the golden
  set — which we wrote — and always pass. A metric that cannot fail is worse
  than no metric, because it looks like evidence. `tests/test_thresholds.py`
  fails if anyone re-adds it.

### The catalog contradicts itself on scale

`builtin.task_adherence` v16 reports a metric of type **`boolean`** while its own
`init_parameters.threshold` advertises a **1–5** range.

A threshold of 4.0 therefore failed *every single case* while the judge's own
reason text read as an unambiguous pass. That is the worst possible failure
shape for this demo: it is indistinguishable from a genuine regression, and the
instinct on stage would be to blame the agent.

`verify_scales()` now reads the live catalog before a run and fails loudly if a
configured threshold is unreachable on the declared scale. Scale drift becomes a
startup error instead of a false accusation against the agent.

### task_adherence punishes a correct refusal, so it was dropped

Six of the thirty golden cases have a refusal as the **correct** answer — "there
is no Meridian Small Cap Value Fund", "I can't give you a client's account
number". Declining is the behaviour the demo exists to prove.

`builtin.task_adherence` measures whether the agent *completed the task*, and its
`data_schema` accepts only `query`, `response`, `tool_definitions` and
`messages`. There is **no field for the intended outcome**. It cannot be told
that refusing was right, so it reads a correct refusal as a failed task.

Verified live: v2 was asked for the expense ratio of a fund that does not exist,
correctly answered "I can't find that in Meridian's documents", and scored 0 —
failing the gate on the single most persuasive moment in the deck.

It is dropped, for the same reason `retrieval` is: a metric that cannot be made
to agree with the desired behaviour is worse than no metric, because a red cell
on stage reads as evidence. Nothing is lost in detection — across every run it
scored v1 a perfect 1.00 and never caught a staged failure. Groundedness catches
fabrication; the compliance rubric judges whether a refusal was handled well.

`relevance` and `intent_resolution` show a milder form of the same bias: both
mark down refusal cases. They are kept because they still pass comfortably and
do catch real problems, but the effect is visible in the per-case rollup and the
demo guide tells the presenter how to answer it rather than hoping nobody asks.

**The general lesson, and the one worth saying to a compliance audience:**
choosing evaluators is engineering, not configuration. Three of Foundry's
built-ins were wrong for this workload in three different ways — one graded the
answer key, one contradicted its own scale, one punished the correct answer.

## Judge model

The judge moves from `gpt-5.4-mini` to **`gpt-4.1-mini`**. The evaluation stack
sends `max_tokens`, which reasoning models reject outright — every built-in
evaluator errored. `gpt-4.1-mini` is non-reasoning and accepts `max_tokens`,
`temperature: 0.0` **and** `seed`, so scoring is *more* reproducible than before,
not less.

Note the asymmetry: the agent (`gpt-5.5`) cannot take a seed and the judge can.
Reproducibility of the *verdict* is what decides pass or fail, so this is the
right side to pin.

## Consequences

### Positive
- Every run is a first-class, portal-visible Foundry object with a permanent
  record. The demo's central claim is now demonstrable in the product.
- No local orchestration: the agent is exercised exactly as a caller would
  exercise it, through the service.
- One fewer dependency, and no local/portal drift to explain.

### Negative
- Groundedness measures faithfulness to `ground_truth`, not to retrieved
  context. This is a real weakening and is stated openly rather than hidden.
- Instruction-following is now judged only by our own rubric. `task_adherence`
  was the one Microsoft-authored evaluator answering "did it stay inside its
  instructions", and dropping it means that question is answered by a control we
  wrote. More precise, less independent.
- The pipeline depends on preview REST surfaces with known spec inaccuracies.
  `_foundry.py` concentrates that knowledge in one place so it ages in one place.
- Iteration is slower: every scoring change costs a live run.

### Neutral
- Runs cost money, so `--limit` exists for smoke runs. Partial runs are labelled
  and can never be mistaken for a gate result.

## Verified results

Full 30-case runs, 2026-09-21, with every metric scored on all 30 cases:

| Metric | v1 | v2 | Threshold |
|---|---|---|---|
| groundedness | 5.00 | 4.97 | 4.00 |
| relevance | 4.93 | 4.77 | 4.00 |
| intent_resolution | 4.93 | 4.90 | 4.00 |
| compliance_safe_answer | 0.87 | 1.00 | 1.00 |
| gate | **exit 1** | **exit 0** | |

Note what v1 fails on. Not one of its four failures (MWP-008, MWP-017, MWP-022,
MWP-024) is a hallucination — every figure it states is correct, and every one is
uncited. The demo's sharpest claim turned out not to be "the agent lies" but "the
agent is right in a way you cannot audit", which is the more realistic finding in
a regulated firm.

## Revisit when

Foundry exposes tool outputs to evaluators. At that point groundedness should be
re-pointed at retrieved context and `retrieval` should return — both are the
stronger measurements, and they are what this demo would prefer to show.

If `task_adherence` gains a ground-truth or expected-outcome input, reinstate it:
the question it asks is the right one, only its inputs were insufficient.
