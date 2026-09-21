# Foundry Evals Demo — Meridian Wealth Partners

A 45-minute, end-to-end demonstration of **Microsoft Foundry Evaluations**: how
you prove an agent is correct, grounded, and compliant — and how you stop a bad
one from shipping.

Built around a fictional wealth-management firm, because "the model said
something plausible but wrong" is a very different conversation when the subject
is an advisory fee.

> **All data in this repository is synthetic.** No real client, account, or
> personal information is present. See `docs/demo-traps.md`.

---

## What it shows

Two agents. Same model, same documents, same knowledge base. They differ **only**
in their instructions and retrieval settings — enforced by a test
(`tests/test_agent_parity.py`), so the comparison is honest rather than rigged.

| | v1 — naive | v2 — hardened |
|---|---|---|
| Instructions | 3 sentences | 5 explicit guards |
| Citations | off | required |
| Retrieval | `simple` keyword, top 3 | `vector_semantic_hybrid`, top 5 |
| Gate result | ❌ **exit 1** | ✅ **exit 0** |

Both are evaluated against 30 golden cases covering five failure modes that
matter in financial services:

| Failure mode | Looks like | Caught by |
|---|---|---|
| Hallucinated number | A confident, fabricated fee or return | Groundedness |
| Missing citation | True, but unverifiable | Compliance rubric |
| Missing disclosure | Accurate, and still a regulatory problem | Compliance rubric |
| Stale document | A perfect quote from a superseded schedule | Groundedness + rubric |
| PII leakage | Answers a routine-sounding request with client data | Compliance rubric |

Plus **10 control cases** that should be answered normally — because the cheapest
way to score well on groundedness is to refuse everything, and a scorecard that
does not detect that is not measuring quality.

---

## How it works

**Everything scores inside Foundry.** This repository contains no evaluation
SDK. `run_eval.py` creates an evaluation run over REST with an *agent target*;
Foundry calls the published prompt agent itself, runs the evaluators, and stores
the result. The scorecard in your terminal and the scorecard in the portal are
the same object, not two things that happen to agree.

That is the whole point of the demo, and it was a deliberate change — an earlier
version scored locally and left the portal's Evaluations tab empty, which made
the central claim unprovable. See **ADR-0006**.

```
        ┌──────────────┐
        │ azd up       │  Bicep → corpus → knowledge base → agents → seeding
        └──────┬───────┘
               │  seeds: evaluator catalog entry + golden dataset
               ▼
  ┌──────────────────────────────────────────────┐
  │            Microsoft Foundry                 │
  │                                              │
  │  dataset ──► agent under test ──► AI Search  │
  │                    │                         │
  │                    ▼                         │
  │               judge model                    │
  │        3 built-ins + 1 custom rubric         │
  │                    │                         │
  │                    ▼                         │
  │             evaluation run  ◄── shown in the portal
  └────────────────────┬─────────────────────────┘
                       ▼
             run_eval.py reads scores
             → thresholds → exit 0 / 1
```

### The five metrics

| Metric | Scale | Threshold | What it protects |
|---|---|---|---|
| `groundedness` | 1–5 | 4.0 | Answers trace to source material, not invention |
| `relevance` | 1–5 | 4.0 | The answer addresses the question asked |
| `intent_resolution` | 1–5 | 4.0 | The user's actual goal was met |
| `compliance_safe_answer` | pass/fail | 100% pass rate | Citations, disclosures, PII, supersession |

`compliance_safe_answer` is a **custom weighted-dimension rubric** we author and
publish to Foundry's evaluator catalog (`evaluators/compliance_safe_answer.yaml`
→ `scripts/seed_evaluator.py`). Its threshold is a required *pass rate*, not a
score: there is no acceptable rate of compliance failure.

All thresholds live in `evals.config.yaml`. Nothing environment-specific is
hardcoded in Python.

### Three honest limitations

Stated up front, because a client will find them:

1. **Foundry does not expose agent tool *outputs* to evaluators** — only the
   response and the tool-call trace. So `groundedness` is scored against the
   golden set's `ground_truth` rather than the context this run actually
   retrieved. That is a weaker claim than textbook groundedness.
2. **`retrieval` is not scored at all.** Scored against `ground_truth` it would
   grade the golden set we wrote ourselves and could never fail. A metric that
   cannot fail is worse than no metric, because it looks like evidence.
   `tests/test_thresholds.py` fails if anyone re-adds it.
3. **`task_adherence` is not scored either.** Six golden cases have "say you
   cannot find it" as the *correct* answer, and the evaluator accepts no input
   for the intended outcome — so it scored a correct refusal as a failed task
   and failed the gate on the strongest moment in the demo. `relevance` and
   `intent_resolution` show a milder version of the same bias on refusal cases;
   they stay because they still pass comfortably and catch real problems.

Retrieval quality is instead proven at provision time by a **canary**: the
knowledge base must rank the 2026 fee schedule above the superseded 2025 one, or
`azd up` fails.

### Reproducibility

The agent (`gpt-5.5`) is a reasoning model: it rejects `temperature` and `top_p`,
and the Responses API has no `seed`. Its reproducibility rests on a pinned model
version and a fixed prompt.

The judge (`gpt-4.1-mini`) is non-reasoning by design and accepts
`temperature: 0.0` **and** `seed`. Since the judge is what decides pass or fail,
that is the correct side to pin.

---

## Deploy

Full prerequisites in `docs/prerequisites.md`. **Verify model availability in
your region before you start** — that is the most common first failure.

You need Contributor **and** User Access Administrator on the subscription; the
RBAC module creates role assignments, and Contributor alone cannot.

```bash
cd src/evals
azd up
```

One command. The post-provision hook (`scripts/postprovision.sh`) then:

| Step | Script | Fails the deploy if… |
|---|---|---|
| Push 12 documents into the search index | `index_corpus.py` | fewer than 12 documents land |
| Build the Foundry IQ knowledge base | `setup_knowledge.py` | the recency canary does not rank 2026 above 2025 |
| Publish both prompt agents | `create_agents.py` | either agent cannot answer a grounded question |
| Publish the compliance rubric | `seed_evaluator.py` | the catalog rejects it |
| Register the golden dataset | `seed_dataset.py` | upload or version registration fails |

The smoke test in `create_agents.py` exists because **the agent API does not
validate tools at creation time** — a typo, a missing connection or a missing
role assignment all produce a perfectly green deploy and an agent that fails on
its first question, on stage. Verified: the API accepted a tool of type
`totally_bogus_xyz` without complaint. See ADR-0005.

There is a deliberate 60-second RBAC wait, and the agent smoke test retries for
up to 10 minutes. Search data-plane role propagation took ~5 minutes in testing,
and the resulting error names no identity, role or resource.

### Tear down

```bash
azd down --purge
python scripts/verify_teardown.py
```

`--purge` matters: soft-deleted Foundry accounts block the next deploy with a
name conflict. `verify_teardown.py` checks rather than assumes.

---

## Test

### Locally — no subscription required

Every invariant that can be checked without Azure, is:

```bash
python -m pip install -e ".[dev]"
python -m pytest        # 44 tests
ruff check .
```

| Suite | Guards |
|---|---|
| `test_corpus.py` | synthetic-data rules, planted traps intact, no real-looking PII |
| `test_dataset.py` | 30 cases, failure-mode coverage, control cases present |
| `test_agent_parity.py` | v1 and v2 differ *only* in prompt and retrieval settings |
| `test_gate.py` | exit 1 on quality failure, exit 2 on harness failure — never conflated |
| `test_thresholds.py` | no unreachable threshold, correct data mappings, `retrieval` stays out |
| `test_thresholds.py` | **an errored or skipped evaluator fails the harness rather than being averaged away** |

`test_thresholds.py` exists because expensive live discoveries should cost a
free CI failure next time, not another paid debugging session. The sharpest one:
a full run once reported the `pii_leak` failure mode as **0 failures** when the
compliance rubric had actually *errored* on 2 of those 3 cases, and the pass
rate was computed over the survivors. A gate that cannot distinguish "passed"
from "never ran" protects nothing, so that is now a harness failure (exit 2).

Every guard in this repository has been **tamper-tested**: deliberately broken to
confirm a test actually fails, then reverted. See `docs/tamper-log.md`.

### Against live Azure

```bash
# Cheap smoke — 3 cases. Labelled partial; can never be mistaken for a gate result.
python scripts/run_eval.py --agent meridian-advisor-v1 \
    --dataset-name meridian-smoke --limit 3

# The real gate
python scripts/run_eval.py --agent meridian-advisor-v1 ; echo "exit=$?"   # 1
python scripts/run_eval.py --agent meridian-advisor-v2 ; echo "exit=$?"   # 0
```

Before any run, `verify_scales()` reads the **live** evaluator catalog and fails
loudly if a configured threshold is unreachable on the declared scale. This
exists because `builtin.task_adherence` reported a boolean while advertising a
1–5 threshold range — a 4.0 threshold failed every case while the judge's own
reason text read as a pass, which is indistinguishable from a real regression.
(That evaluator was later dropped for an unrelated reason; the check stays,
because the catalog can drift again.)

Results are written to `results/` as JSON, including the Foundry eval and run
ids so a terminal scorecard can be traced to the portal run it came from.
Partial runs are suffixed `-partial`.

### Last verified results

Full 30-case runs, 2026-09-21, all 30 cases scored on every metric:

| Metric | v1 | v2 | Threshold |
|---|---|---|---|
| groundedness | 5.00 | 4.97 | 4.00 |
| relevance | 4.93 | 4.77 | 4.00 |
| intent_resolution | 4.93 | 4.90 | 4.00 |
| compliance_safe_answer | **0.87** ❌ | **1.00** ✅ | 1.00 |
| **gate** | **exit 1** | **exit 0** | |

v1 fails on four cases — MWP-008, MWP-017, MWP-022, MWP-024 — and not one of them
is a hallucination: its figures are correct and simply uncited. "Correct but
unverifiable" is still a finding in a regulated firm, and it is the failure mode
a demo that only hunts for made-up numbers would miss. See
[`docs/demo-traps.md`](docs/demo-traps.md) for why the three planted traps no
longer fire against a capable model, and why that is the stronger argument.

### From the portal

`azd up` seeds the evaluator and dataset precisely so the presenter can create
the run in the Foundry portal instead. Both paths execute in the same service
and produce the same run object — which is the point worth making on stage.

---

## Layout

```
infra/                 Bicep — Foundry, Search, monitoring, RBAC
corpus/                12 synthetic Meridian documents (3 planted traps)
datasets/              30-case golden dataset
agents/                v1-naive / v2-hardened prompt agent definitions
evaluators/            custom compliance rubric
scripts/               provisioning, seeding, evaluation, teardown
tests/                 corpus, dataset, parity, gate and threshold invariants
docs/                  run-of-show, architecture, traps, threat model, ADRs
specs/                 the spec this was built from
.specify/memory/       the constitution governing it
```

Key scripts:

| Script | Role |
|---|---|
| `_foundry.py` | REST client. Concentrates every quirk of the preview data plane in one place |
| `_common.py` | config loading, credentials, console output |
| `index_corpus.py` | embeds and pushes the corpus into Azure AI Search |
| `setup_knowledge.py` | builds the Foundry IQ knowledge base, runs the recency canary |
| `create_agents.py` | publishes both agents from YAML, smoke-tests grounding |
| `seed_evaluator.py` | publishes the compliance rubric to the evaluator catalog |
| `seed_dataset.py` | registers the golden dataset for portal use |
| `run_eval.py` | creates the Foundry run, applies thresholds, returns the exit code |
| `verify_teardown.py` | proves the environment is actually gone |

## Documentation

| Read this | When |
|---|---|
| `docs/run-of-show.md` | Before presenting — the timed 45-minute script |
| `docs/pre-flight-checklist.md` | 10 minutes before the meeting |
| `docs/demo-traps.md` | To understand what is planted and why |
| `docs/architecture.md` | When someone asks how it is wired |
| `docs/threat-model.md` | When someone asks what could go wrong |
| `docs/day-2.md` | When someone asks "how does this live in our SDLC?" |
| `docs/adr/` | When someone asks why it was built this way |

The ADRs carry the decisions that cost the most to learn:

| ADR | Decision |
|---|---|
| 0001 | Bicep + azd over Terraform |
| 0002 | Knowledge base built over REST |
| 0003 | Two agent versions rather than one tuned agent |
| 0004 | Documents pushed into the index, not staged via a blob indexer |
| 0005 | Agents ground through an AI Search connection, not the knowledge base |
| **0006** | **Evaluation runs inside Foundry, not in a local SDK** |

---

## Non-negotiables

From `.specify/memory/constitution.md`, and enforced rather than asserted:

- **No real data.** Synthetic identifiers use reserved-for-fiction formats only,
  verified by test.
- **Keyless.** `allowSharedKeyAccess: false`, `disableLocalAuth: true`. Entra ID
  and managed identity throughout; no key or connection string is emitted as an
  output.
- **One command up, one command down.** With teardown verified, not assumed.
- **Reproducible.** Pinned model versions, fixed prompts, judge `temperature: 0.0`
  and a fixed seed, pinned API version.
- **The gate actually blocks.** Exit 1 for a quality failure, exit 2 for a broken
  harness — deliberately distinct, because conflating them is how a gate stops
  protecting anything.

## Cost

Consumption-billed, and the dominant cost is model inference during evaluation:
roughly 30 agent calls plus ~150 judge calls per full run. Azure AI Search runs
on Basic and is the main idle cost.

Use `--limit` while iterating. Teardown is `azd down --purge`; leaving the
environment running overnight is the only way this gets expensive.

---

## Status

Infrastructure, corpus, dataset, agents, evaluation pipeline and test suite are
complete, deployed and verified against live Azure. Evaluation runs execute
server-side and appear in the Foundry portal.

The pipeline depends on **preview REST surfaces** (`2025-11-15-preview`) with
known spec inaccuracies, all documented in ADR-0006 and isolated in
`scripts/_foundry.py`. Expect to re-verify when the API version moves.
