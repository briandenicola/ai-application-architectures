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

Two agents. Same model, same temperature, same seed, same documents. They differ
only in their instructions and retrieval settings — enforced by a test, so the
comparison is honest.

| | v1 — naive | v2 — hardened |
|---|---|---|
| Instructions | 3 sentences | 5 explicit guards |
| Citations | off | required |
| Gate result | ❌ **exit 1** | ✅ **exit 0** |

Both are evaluated against 30 golden cases covering five failure modes that
matter in financial services:

| Failure mode | Looks like | Caught by |
|---|---|---|
| Hallucinated number | A confident, fabricated fee or return | Groundedness |
| Missing citation | True, but unverifiable | Compliance rubric |
| Missing disclosure | Accurate, and still a regulatory problem | Compliance rubric |
| Stale document | A perfect quote from a superseded schedule | Retrieval + rubric |
| PII leakage | Answers a routine-sounding request with client data | Task adherence + rubric |

Plus **10 control cases** that should be answered normally — because the cheapest
way to score well on groundedness is to refuse everything, and a scorecard that
does not detect that is not measuring quality.

---

## Quickstart

Full prerequisites in `docs/prerequisites.md`. **Verify model availability in
your region before you start** — that is the most common first failure.

```bash
cd src/evals

# 1. Provision everything — infra, corpus upload, knowledge base, both agents
azd up

# 2. Watch the naive agent fail the gate
python scripts/run_eval.py --agent meridian-advisor-v1
echo "exit=$?"        # 1

# 3. Watch the hardened agent pass
python scripts/run_eval.py --agent meridian-advisor-v2
echo "exit=$?"        # 0

# 4. Tear it all down
azd down --purge
python scripts/verify_teardown.py
```

`azd up` runs a post-provision hook that uploads the 12 documents, builds the
Foundry IQ knowledge base, verifies indexing, and creates both agents. It fails
loudly if the knowledge base is not actually usable — a half-indexed index is the
single most common way this kind of demo dies quietly.

### Running it without Azure

The invariants are all testable locally:

```bash
python -m pip install -e ".[dev]"
python -m pytest        # 35 tests, no subscription required
```

---

## Layout

```
infra/                 Bicep — Foundry, Search, monitoring, RBAC
corpus/                12 synthetic Meridian documents (3 planted traps)
datasets/              30-case golden dataset
agents/                v1-naive / v2-hardened prompt agents
evaluators/            custom compliance rubric grader
scripts/               upload, knowledge setup, agent creation, eval, teardown
tests/                 corpus, dataset, agent-parity and gate invariants
docs/                  run-of-show, architecture, traps, threat model, ADRs
specs/                 the spec this was built from
.specify/memory/       the constitution governing it
```

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

---

## Non-negotiables

Taken from `.specify/memory/constitution.md`, and enforced rather than asserted:

- **No real data.** Synthetic identifiers use reserved-for-fiction formats only,
  verified by test.
- **Keyless.** `allowSharedKeyAccess: false`, `disableLocalAuth: true`. Entra ID
  and managed identity throughout; no key or connection string is emitted as an
  output.
- **One command up, one command down.** With teardown verified, not assumed.
- **Reproducible.** Temperature 0.0, fixed seed, pinned API version.
- **The gate actually blocks.** Exit 1 for a quality failure, exit 2 for a broken
  harness — deliberately distinct, because conflating them is how a gate stops
  protecting anything. Tamper-tested; see `docs/tamper-log.md`.

## Cost

Consumption-billed. The dominant cost is model inference during evaluation —
roughly 60 model calls per run plus judge calls. Azure AI Search runs on Basic.

> Measure it on your first run and record it here. Teardown is
> `azd down --purge`; leaving the environment running overnight is the only way
> this gets expensive.

---

## Status

The infrastructure, corpus, dataset, agents, harness and local test suite are
complete and green. The Foundry IQ REST payloads and the eval SDK calls are
pinned to API `2026-04-01` and need verification against a live deployment before
first client use — see the open items in `specs/001-foundry-evals-demo/spec.md §7`.
