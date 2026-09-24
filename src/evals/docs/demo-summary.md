# Where this demo stands

One page. Deeper detail lives in the documents linked from each section.

Last updated 2026-09-24.

---

## The idea

Two agents, identical in every respect except their instructions, answer the
same questions over the same documents. One is graded by Microsoft Foundry and
fails. The other passes. Everything a client is asked to believe is a Foundry
artifact they can open in the portal, not a number printed by a script.

The corpus is entirely synthetic. The failures are real.

---

## What is built

Three tracks, each a corpus plus a naive/hardened agent pair plus a golden set.

| Track | Corpus | Agents | Golden set | Registered? |
|---|---|---|---|---|
| **Advisor** — wealth-management compliance | `corpus/` (12 docs) | `meridian-advisor-v1` / `-v2` | 30 cases, 3 refusals | ✅ full |
| **FinOps** — AI platform cost governance | `corpus-finops/` (19 docs) | `meridian-finops-v1` / `-v2` | 26 cases, 3 refusals | ✅ full |
| **People analytics** — HR inference | `corpus-hr/` (22 docs) | `meridian-people-v1` / `-v2` | 25 cases, 16 refusals | ⚠️ corpus + agents only |

"Registered" means the track has `dataset_*`, `evaluators_*` and `thresholds_*`
in `evals.config.yaml` and can therefore be run and gated. HR has a corpus, an
indexed search index, a published agent pair and a drafted golden set, but no
rubric and no config registration — so it cannot be scored yet. See issue #11.

**Scoring.** Three Foundry built-ins (groundedness, relevance,
intent_resolution) plus one custom rubric per track, published to the Foundry
evaluator catalog and selectable in the portal:

- `meridian-compliance-safe-answer` v4 — 6 dimensions
- `meridian-finops-defensible-answer` v2 — 8 dimensions

Nothing is scored locally. Foundry calls the agent itself
(`target.type = azure_ai_agent`), runs every evaluator server-side, and stores
the run, so the terminal scorecard and the portal scorecard are the same object.

**Harness.** 288 tests, no Azure required. Exit codes are load-bearing:
`0` pass, `1` quality threshold breached, `2` harness cannot run. Collapsing 1
and 2 is how a gate stops protecting anything.

---

## How to demo

Full scripts: [`docs/run-of-show.md`](run-of-show.md) (advisor, 45 min) and
[`docs/finops-run-of-show.md`](finops-run-of-show.md). Pre-flight:
[`docs/pre-flight-checklist.md`](pre-flight-checklist.md).

The spine is four beats:

1. **Show the documents.** Ordinary, boring, synthetic. Two fee schedules, one
   superseded. Nothing in either says which is current.
2. **Ask v1 a reasonable question.** It answers fluently and wrongly, or
   correctly but unverifiably. Nothing about the answer looks wrong.
3. **Run the gate.** `run_eval.py --agent ...-v1` → **exit 1**, with the
   failing cases named and the judge's own reasoning attached.
4. **Run v2.** Same model, same documents, same questions, different
   instructions → **exit 0**. Then open the same run in the portal.

```bash
# Cheap smoke — 3 cases, labelled partial, can never be mistaken for a gate result
python scripts/run_eval.py --agent meridian-advisor-v1 --dataset-name meridian-smoke --limit 3

# The gate
python scripts/run_eval.py --agent meridian-advisor-v1 ; echo "exit=$?"   # expect 1
python scripts/run_eval.py --agent meridian-advisor-v2 ; echo "exit=$?"   # expect 0
```

The FinOps track swaps in with `--corpus finops`.

---

## Topics this covers

**For a compliance or risk audience**

- Ungrounded figures — correct arithmetic over invented inputs
- Personalised advice from a system not licensed to give it
- Superseded documents that carry no warning on their face
- Client PII surfacing because it was present in a source document
- Required disclosures silently dropped

**For a platform or FinOps audience**

- Projections presented as actuals; metered versus billed
- Derived per-unit rates that appear in no document
- Recommendations built on a manufactured baseline

**For an HR or people-analytics audience** (built, not yet gated)

- Inference about individuals from aggregate data
- Small-cell re-identification
- Causal claims from correlational workforce data
- Recommendations the requester has no authority to act on

**The methodological point, and the one that travels furthest.** A trap whose
answer is written in the corpus is a reading-comprehension test, not a
governance test. Probing round 1 on the HR track asked "is X true?" where X was
discussed in the documents — 4 of 12 fired, because v1 simply retrieved the
caveat and read it aloud. Round 2 asked for figures the corpus does not contain
— 9 of 9 fired, and v2 closed all nine. Three of six FinOps traps had failed
the same way. Write traps against what the corpus *lacks*.
See [`docs/hr-traps.md`](hr-traps.md).

**The engineering point.** Every guard in this repo has been deliberately
broken, watched to fail by name, and reverted, with the result recorded in
[`docs/tamper-log.md`](tamper-log.md) — 22 entries. That log exists because the
most expensive recurring failure here has never been a broken guard. It is a
guard reporting green while protecting nothing, which has now appeared in six
distinct disguises.

---

## What is not proven

This section is the point of the document. Do not describe anything below as a
working control in front of a client.

- **The published v1/v2 scorecard is stale.** The last verified full run was
  2026-09-21 (v1 exit 1 on 4 cases, v2 exit 0). Since then the corpora were
  re-indexed with `doc_id` in the body and both rubrics gained a
  `citation_discipline` dimension. **The run needs repeating before it is shown.**
- **`citation_discipline` is UNVERIFIED.** Foundry accepts the citation columns
  in `data_mapping` and echoes them back, but it is not established that the
  rubric judge receives them. If it does not, the check is inert while looking
  wired. The settling experiment is two cases with identical canned responses
  differing only in `forbidden_citations`. Issue #14.
- **MAP-014 no longer discriminates** — v1 now answers it correctly. It should
  be rewritten rather than dropped: v1 still mislabels the October rates as
  "Current prices used". Issue #13.
- **The HR track has never been scored.** No rubric, not registered.
- **A full both-version FinOps run has never been produced.**

---

## Open issues

- **#11** — HR people-analytics track: rubric, registration, first scored run
- **#13** — two unplanted FinOps failures worth promoting; re-probe first
- **#14** — citation scoring: upstream half fixed and verified, downstream half
  wired but unverified

---

## The rules that are not negotiable

From [`.specify/memory/constitution.md`](../.specify/memory/constitution.md):

- Agent pairs differ **only** in `instructions` and `knowledge.retrieval`.
  Anything else invalidates the central claim, and `test_*_agent_parity.py`
  fails.
- Keyless auth throughout — Entra ID and managed identity. No connection
  strings, keys or SAS tokens, and never as an IaC output.
- Synthetic data only. Reserved-for-fiction identifiers: SSN area `000`, phone
  `(212) 555-01xx`, email `@example.com`.
- Break every guard before believing it, and write down what happened.
