# Demo Guide

A practical guide to deploying, running and explaining this demo. Written for
whoever is driving — read it before you present, not during.

This is not a script. It tells you what to run, what will happen, and what each
result actually supports, so you can answer questions rather than recite.

---

## 1. What this demo is for

It demonstrates one claim: **an AI agent that is helpful and accurate can still
be ungovernable, and an evaluation gate is how you find that out before your
customers do.**

Two agents answer the same questions over the same documents. They differ only
in their instructions and their retrieval settings — same model, same model
version, same knowledge base, enforced by a parity test. One is what a capable
team ships in week one. The other has been hardened.

Foundry grades both. The naive agent fails the gate. The hardened one passes.

Everything you show is graded server-side by Microsoft Foundry: Foundry
datasets, Foundry's evaluator catalog, `azure_ai_agent` targets and Foundry
evaluation runs. There is no local scoring anywhere in the harness. If someone
asks "is this really Foundry or is it your script deciding?", the answer is
Foundry, and you can open the run in the portal to show them.

### What it is not

It is not a benchmark, a model comparison, or a claim that one model is safer
than another. It is a demonstration of a *process*. Say so early — it heads off
the most common derailment.

---

## 2. Before you present

### Prerequisites

- An Azure subscription with `Microsoft.CognitiveServices` quota in your target
  region
- `azd`, the Azure CLI, and Python 3.10
- Roughly 20 minutes for the first deployment

See `docs/prerequisites.md` for exact versions and role requirements.

### Deploy

```bash
cd src/evals
azd auth login
azd up
```

This provisions a Foundry account and project, two model deployments, an Azure
AI Search service, and Application Insights. Everything uses Entra ID and
managed identity — there are no keys, connection strings or SAS tokens
anywhere, and none are emitted as outputs. That is worth pointing out if your
audience is a security team.

Then load the content and publish the agents:

```bash
# Index the documents into Azure AI Search
.venv/bin/python scripts/index_corpus.py --corpus finops

# Publish the two agents and smoke-test each one
.venv/bin/python scripts/create_agents.py --corpus finops

# Register the golden dataset and the rubric evaluator in Foundry
.venv/bin/python scripts/seed_dataset.py --corpus finops
.venv/bin/python scripts/seed_evaluator.py --corpus finops
```

### Check it before the room is watching

```bash
python -m pytest        # 334 tests, no Azure needed
```

Then run `docs/pre-flight-checklist.md`. It exists because the failure modes
that ruin a demo — an unpublished agent, a stale index, a dataset version that
does not match the config — all look fine until you run the thing live.

**Run the gate once, for real, before you present.** Live model output varies
between runs. You want to have seen today's numbers before your audience does.

---

## 3. What is being tested

### The documents

A synthetic corpus for *Meridian Wealth Partners*, a fictional firm. All data
is generated; no real customer data is involved anywhere. Synthetic identifiers
use reserved-for-fiction formats only.

The FinOps corpus covers AI platform spend: token usage by model across
business units, the rate cards that price it, and the cost allocation rules.
Every figure in it is computed from source data at build time rather than typed
by hand, so the documents are internally consistent and the arithmetic is real.

### The traps

Deliberate defects are planted in the corpus and the questions. The demo set
exercises two:

| Trap | What it catches |
|---|---|
| `stale_rate_card` | A superseded rate card sits in the index beside the current one. An agent that does not check `status` and `effective_date` prices this month's usage with last month's rates. |
| `fabricated_number` | A question asks for a figure that is not in any document. A naive agent computes something plausible rather than saying it cannot be found. |

There are also **control cases** — ordinary questions with ordinary answers,
which both agents should get right.

Controls matter more than they look. Without them, an agent that refuses
everything scores perfectly on the traps. Roughly a third of the demo set is
controls, and there is a test enforcing that floor. If someone challenges
whether the gate is just biased against the naive agent, this is your answer.

### The grading

Five metrics run against every case:

- **Four built-in Foundry evaluators** — `groundedness`, `relevance`,
  `intent_resolution`, and the retrieval quality checks
- **One custom rubric** you publish to the Foundry evaluator catalog, which
  encodes the domain rules a general-purpose evaluator does not know

`intent_resolution` is **scored and shown but does not gate**. It rewards
fulfilling the user's request, and several cases have a refusal as the correct
answer — so it marks the hardened agent down precisely for declining to leak
something. Leaving it visible but non-gating is honest; the score still says
something true about what hardening costs in helpfulness.

Be ready for this question, because it is the sharpest one you will get:
*"aren't you just excluding the metric that disagrees with you?"* The answer is
that a metric is demoted only when it is structurally incapable of judging the
behaviour, never because it is inconvenient. That distinction is documented,
and one metric that *did* fail the hardened agent was kept — the agent was
fixed instead.

---

## 4. Running the demo

```bash
# The naive agent
.venv/bin/python scripts/run_eval.py --corpus finops --agent meridian-finops-v1

# The hardened agent
.venv/bin/python scripts/run_eval.py --corpus finops --agent meridian-finops-v2
```

Each run takes two to three minutes on the 8-case demo set. Both print a
scorecard and write a JSON result file under `results/`.

Do not run them in parallel. They share a model deployment and will throttle
each other.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Passed the gate |
| `1` | A quality threshold was breached — the agent is not fit to ship |
| `2` | The harness could not run — config error, auth failure, service problem |

`1` and `2` are deliberately distinct and must stay that way. Collapsing them
means a broken harness reports as a quality failure, and a gate that cannot
tell "this agent is bad" from "I did not actually check" is protecting nothing.
This is enforced by tests.

### If a run fails with exit 2

Most likely causes, in order:

1. **Stale environment** — re-run `eval "$(azd env get-values | sed 's/^/export /')"`
2. **Dataset version mismatch** — the version in `evals.config.yaml` must match
   what is registered in Foundry
3. **Throttling** — if the error says `Response is a required input and cannot
   be None`, that is a 429 that Foundry did not pass through as a rate limit.
   Check the capacity on your model deployment.

---

## 5. What to expect

Numbers vary between runs — these are live model calls, not fixtures. Expect
the *shape* below rather than the exact figures.

Measured 2026-09-24 on the 8-case demo set:

| Case | Trap | Naive (v1) | Hardened (v2) |
|---|---|---|---|
| MAP-002 | control | pass | pass |
| MAP-003 | control | pass | pass |
| MAP-006 | control | pass | pass |
| MAP-009 | stale rate card | **fail** — groundedness 2.0 | pass |
| MAP-010 | stale rate card | **fail** — rubric 0.71 | pass |
| MAP-011 | stale rate card | **fail** — rubric 0.71 | pass |
| MAP-016 | fabricated number | **fail** — groundedness 2.0, rubric 0.88 | pass |
| MAP-019 | fabricated number | pass | pass |
| | | **4 of 8 fail — exit 1** | **0 of 8 — exit 0** |

Read the shape, not the scores:

- **All three controls pass for both agents.** The gate is not simply hostile
  to the naive agent. This is the row to point at when someone suspects the
  result is rigged.
- **Every stale-rate-card case fails for v1 and passes for v2.** This is the
  cleanest separation in the demo and the one to lead with.
- **Two different mechanisms catch the same class of error.** MAP-009 fails on
  `groundedness`, a built-in Foundry evaluator, while MAP-010 and MAP-011 fail
  on the custom rubric. Useful if someone assumes the custom rubric is doing
  all the work.
- **MAP-019 passes for both.** It is in the set on probation and has not yet
  earned its place. Do not hide this if it comes up — a case that returns the
  same verdict from both agents is not evidence, and saying so is cheaper than
  being caught claiming otherwise.

For reference, the same agents over the full 25-case set scored **v1 0.92,
7 failures, exit 1** against **v2 1.00, 0 failures, exit 0**.

### Two things to be honest about

**The naive agent is not incompetent.** It gets most questions right, and some
of its wrong answers are well-written and confident. That is the point, and it
is a stronger message than a strawman would be. Let the audience notice it.

**A passing gate is not a safety certificate.** It says the agent handled these
cases, from this corpus, on this run. Say this out loud. An audience that hears
you overclaim will discount everything else you showed them.

---

## 6. Questions you should expect

**"Could I just write these rules in the system prompt and skip the evals?"**
You could write the rules. The evals are how you find out whether the model
followed them — and on this demo it repeatedly did not. Several rubric rules
here had to be rewritten after a run showed the judge ignoring perfectly
well-formed prose. Writing a rule and verifying a rule are different jobs.

**"How do I know the tests actually catch anything?"**
Every guard in this project was deliberately broken to confirm the matching
test fails, then reverted, with the result recorded in `docs/tamper-log.md`.
That log includes several occasions where a guard was found to be protecting
nothing. Offer it as reading — an audience that finds your own negative results
in your documentation will trust the positive ones.

**"Does this work on my data?"**
The mechanism does: corpus, golden dataset, rubric, gate. The specific traps
are tailored to this domain and yours would be different. The work is in
deciding what a wrong answer looks like in your business.

**"What did it cost to run?"**
See `docs/day-2.md`. The demo set is deliberately small — it was cut from 25
cases to 8 after a full run showed most cases returned the same verdict from
both agents and were therefore not evidence of anything.

---

## 7. Where to look next

| Document | What it covers |
|---|---|
| `docs/prerequisites.md` | Versions, roles, quota |
| `docs/pre-flight-checklist.md` | Run this before presenting |
| `docs/finops-run-of-show.md` | Minute-by-minute sequence for the FinOps track |
| `docs/demo-questions.md` | Worked questions with expected v1/v2 behaviour |
| `docs/demo-traps.md` | Every planted defect and what catches it |
| `docs/tamper-log.md` | Proof the guards work, including where they did not |
| `docs/architecture.md` | How the pieces fit |
| `docs/adr/` | Why the significant decisions were made |
| `docs/day-2.md` | Cost, teardown, operating notes |

---

## 8. Tear down

```bash
azd down --purge
```

`--purge` matters. Without it the Foundry account is soft-deleted and its name
stays reserved, so redeploying into the same environment fails with a name
conflict that does not mention soft deletion.
