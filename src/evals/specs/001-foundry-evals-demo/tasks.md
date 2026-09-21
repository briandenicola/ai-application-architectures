# Tasks — Spec 001

Ordered, incremental. Each task has a verifiable exit condition. `⛔` marks tasks
that touch the user's machine or Azure subscription and therefore require explicit
confirmation before execution.

---

## Phase 0 — Pre-flight

| ID | Task | Exit condition |
|----|------|----------------|
| **T0.1** ⛔ | Verify `centralus` supports `gpt-5.5`, `gpt-4.1-mini`, `text-embedding-3-large` and that quota exists | Model + quota confirmed, or region changed to the fallback and `evals.config.yaml` updated (resolves O1) |
| **T0.2** ⛔ | Pin and record tool versions: `azd`, `az`, Bicep CLI, `azd ai` extension, Python | `docs/prerequisites.md` lists exact versions (resolves O2) |
| **T0.3** | Decide Bicep vs. REST for knowledge source/base at the pinned API version | ADR-0002 written (resolves O3) |
| **T0.4** | Clean up stray `.azure/simple/` azd env in `src/evals` | Directory removed or relocated; `.gitignore` covers `.azure/` (resolves O5) |

## Phase 1 — Scaffold

| ID | Task | Exit condition |
|----|------|----------------|
| **T1.1** | Generate the repo scaffold under `src/evals` via `scripts/bootstrap-repo.mjs` | Tree matches `spec.md`; `--dry-run` and `--force` both behave |
| **T1.2** | `pyproject.toml`, `ruff`, `pyright`, `pytest` config | `ruff check` and `pyright` pass on an empty project |
| **T1.3** | Copilot guardrail files: `copilot-instructions.md`, prompts, `SECURITY.md`, `CODEOWNERS`, `dependabot.yml` | Files present and accurate to this spec |
| **T1.4** | `evals.config.yaml` per `data-model.md § 4` | Loads and validates against a schema test |

## Phase 2 — Corpus

| ID | Task | Exit condition |
|----|------|----------------|
| **T2.1** | Author the 12 Meridian documents per `data-model.md § 1` | All 12 present; front matter validates; every doc carries the SYNTHETIC banner |
| **T2.2** | Plant the stale trap: 2025 fee schedule contradicts 2026 on ≥ 3 tiers | A diff table in `docs/demo-traps.md` shows the contradictions |
| **T2.3** | Plant the PII trap in `meridian-ips-client-aa1042` using reserved patterns only | `tests/test_corpus.py` asserts no pattern outside the reserved set |
| **T2.4** | `tests/test_corpus.py`: banner, front matter, manifest consistency, PII patterns | `pytest` green |

## Phase 3 — Infrastructure

| ID | Task | Exit condition |
|----|------|----------------|
| **T3.1** | `infra/main.bicep` + modules per `contracts.md § 1` | `az bicep build` clean; no secret outputs |
| **T3.2** | Role assignments, resource-scoped and least-privilege | Review against the contract table; no subscription-scope grants |
| **T3.3** | `azure.yaml` with `postprovision` hooks and `azd down` verification | `azd provision --preview` succeeds |
| **T3.4** ⛔ | First real `azd up` into a scratch subscription | Completes unattended; all contract outputs populated |
| **T3.5** ⛔ | `azd down --purge` + verification script | Resource group gone; no soft-deleted Foundry accounts remain |

## Phase 4 — Knowledge (Foundry IQ)

| ID | Task | Exit condition |
|----|------|----------------|
| **T4.1** | `scripts/index_corpus.py` — idempotent, MI-authenticated embed + push into index `meridian-docs` | Re-run is a no-op; 12 documents present |
| **T4.2** | `scripts/setup_knowledge.py` — create knowledge source + knowledge base per `contracts.md § 3` | Idempotent; exits 0 only when all three post-conditions pass |
| **T4.3** | Canary retrieval test: 2026 fee schedule outranks 2025 | Assertion passes; if not, tune the retrieve-time reranker threshold or the v2 recency guard |
| **T4.4** | Portal verification of citations resolving to indexed documents | Screenshot captured for the fallback deck |

## Phase 5 — Agents

| ID | Task | Exit condition |
|----|------|----------------|
| **T5.1** | `agents/v1-naive.agent.yaml` | Reproduces all five failure modes when probed manually |
| **T5.2** | `agents/v2-hardened.agent.yaml` | Differs from v1 only in `instructions` + `knowledge.retrieval` |
| **T5.3** | `tests/test_agent_parity.py` — enforce the "only two fields differ" invariant | `pytest` green |
| **T5.4** | `scripts/create_agents.py` — idempotent create-or-update | Re-run is an update; agent IDs written to `.azure` env |

## Phase 6 — Dataset & Evaluators

| ID | Task | Exit condition |
|----|------|----------------|
| **T6.1** | Author 30 cases in `datasets/meridian-golden-v1.jsonl` | Tag distribution matches `data-model.md § 2` exactly |
| **T6.2** | `tests/test_dataset.py` — all 7 dataset invariants | `pytest` green |
| **T6.3** | Verify every `ground_truth` is retrievable from the corpus (not eyeballed) | Retrieval assertion passes for all 30 |
| **T6.4** | `evaluators/compliance_safe_answer.yaml` rubric grader | Emits boolean + reason on a smoke case |
| **T6.5** | Wire the five built-in evaluators with the pinned judge model | Config validates |

## Phase 7 — Harness & Gate

| ID | Task | Exit condition |
|----|------|----------------|
| **T7.1** | `scripts/run_eval.py` per `contracts.md § 4` | Exit codes 0/1/2 behave; result JSON matches schema |
| **T7.2** | Terminal summary table + per-tag rollup | Readable on a projector at 14pt |
| **T7.3** ⛔ | Run v1 → assert it fails ≥ 3 metrics and the rubric | Red scorecard reproduced twice |
| **T7.4** ⛔ | Run v2 → assert it passes all six thresholds | Green scorecard reproduced twice |
| **T7.5** | Assert the `grounded_happy` control cases pass under v2 (no over-refusal) | 10/10 pass |
| **T7.6** ⛔ | Verify `azd ai agent eval run` yields the same verdict as the portal | Verdicts identical for both agents |

## Phase 8 — Tamper Tests (required by the constitution)

| ID | Task | Exit condition |
|----|------|----------------|
| **T8.1** | For each of the five guards in v2: remove it, confirm the matching evaluator flips to fail, revert | 5/5 guards proven; results recorded in `docs/tamper-log.md` |
| **T8.2** | Corrupt the dataset (break an invariant) and confirm `test_dataset.py` fails, then revert | Test proven |
| **T8.3** | Force a threshold breach and confirm `run_eval.py` exits 1 | Gate proven to block |

## Phase 9 — Demo Assets

| ID | Task | Exit condition |
|----|------|----------------|
| **T9.1** | `docs/run-of-show.md` — 45 min: framing 8 / architecture 7 / grounding 7 / v1 failure 10 / fix + v2 8 / terminal gate + close 5 | Timed dry run lands within ± 3 min |
| **T9.2** | `docs/architecture.md` + Mermaid diagram | Renders in GitHub |
| **T9.3** | `docs/threat-model.md` | Covers prompt injection via corpus, PII leakage, over-permissive RBAC, judge-model gaming |
| **T9.4** | Fallback assets: committed pre-recorded eval output + screenshots | Demo runnable with zero live Azure calls |
| **T9.5** | `docs/pre-flight-checklist.md` — quota, index population, agent existence | Runnable 10 minutes before a meeting |
| **T9.6** | `docs/day-2.md` — GitHub Actions gate + continuous evaluation (designed, not built) | One slide's worth of concrete next steps |

## Phase 10 — Close-out

| ID | Task | Exit condition |
|----|------|----------------|
| **T10.1** | `README.md` — 5-minute quickstart | A colleague can stand it up unaided |
| **T10.2** ⛔ | Measure hourly cost of the deployed environment | Figure recorded in README (resolves O6) |
| **T10.3** | Full quality gate green: ruff, pyright, pytest, bicep build, gitleaks | All pass |
| **T10.4** ⛔ | Final clean-subscription rehearsal: `azd up` → demo → `azd down --purge` | End-to-end, unattended, verified |

---

## Dependency Graph

```
T0 ──► T1 ──► T2 ──► T3 ──► T4 ──► T5 ──► T6 ──► T7 ──► T8 ──► T9 ──► T10
         │             │                    │
         └─► T1.4 ─────┘                    └─► T6.4 (rubric can start early)
```

`T2` (corpus) and `T3` (infra) are independent after `T1` and may run in parallel.
Everything from `T4` onward is strictly sequential — the knowledge base must be
healthy before agents mean anything, and agents must exist before evaluations do.

---

## Suggested Cut Line

If time is short, ship Phases 0–8 plus `T9.1` and `T9.4`. That yields a working,
proven, rehearsable demo. `T9.3`, `T9.6`, and `T10.2` are polish.

The one thing that must **not** be cut is **Phase 8**. A demo about proving quality
that never proves its own guards work would be self-refuting.
