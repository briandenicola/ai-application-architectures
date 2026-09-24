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

## The advisor gate, verified end to end

Reproduced 2026-09-24, both agents against compliance rubric **v8**, 30 of 30
cases scored:

| | v1 naive | v2 hardened |
|---|---|---|
| groundedness | 4.97 ✅ | 4.93 ✅ |
| relevance | 4.83 ✅ | 4.87 ✅ |
| intent_resolution (report-only) | 4.90 | 4.93 |
| compliance_safe_answer | **0.89 ❌ — 10 of 30** | **1.00 ✅ — 0 of 30** |
| gate | **exit 1** | **exit 0** |

The point to make on stage is that **every built-in metric passes for v1**. A
team watching a standard quality dashboard ships this agent. The governance
rubric is the only thing that stops it, and it stops it on ten cases — three of
which have no planted trap at all, and fail purely because correct figures are
uncited.

### The gate was failing the hardened agent for refusing to leak PII

Worth telling, because it is the most honest thing in the demo. The first full
run failed v2 on three cases: declining to give out client contact details for
account AA-1042, declining to invent a dollar total, declining to state an
expense ratio it could not source. `intent_resolution` rewards fulfilling the
user's request, and six golden cases have a refusal as the correct answer.

Two things were wrong and only one of them was the gate. `intent_resolution` is
now report-only — scored and shown, unable to fail the build — and the rubric's
conditional dimensions now declare inapplicability before they start demanding
things, so a refusal is scored as "not applicable" rather than as a missing
figure. But the last failure was v2's own: it refused correctly and uselessly,
with a bare "I can't find that" and a wall of disclosure. That was fixed in the
agent, not the gate. Demoting `relevance` would have turned the board green
just as fast and left it protecting nothing.

See `docs/tamper-log.md` §T25 and §T26. Three of the four T25 tampers passed on
the first attempt: both gate guards were aimed at test fixtures rather than at
the config and code that actually run.

---

## What is not proven

This section is the point of the document. Do not describe anything below as a
working control in front of a client.

- **A rubric judge cannot verify a figure against the corpus.** It receives the
  query and the response — nothing else. For months four dimensions, two of them
  at weight 10, told it to check the answer against "the retrieved context" it
  has never been given. Asked for a check it cannot perform, the judge does not
  abstain: it scores on plausibility and writes a confident justification. All
  four are now self-contained and say so explicitly
  (`docs/citation-delivery-finding.md`), **but every run produced before
  2026-09-24 was graded partly on plausibility.** The advisor scorecard has
  since been reproduced under the corrected rubric (v8); the FinOps and HR
  tracks have not. Delivering real retrieval to the judge is issue #15.
- **MAP-014 still does not discriminate on recency.** It was rewritten on
  2026-09-24 to target the labelling defect instead of card identification, and
  probed: v1 opened "November 2025 used the October 2025 rate card" — correct.
  The doc_id-in-body change genuinely fixed v1's card identification. The two
  versions still separate on attribution (v1 cites opaque markers and omits the
  disclosure; v2 gives inline doc_ids), so the case still earns its place, but
  its `stale_rate_card` tag no longer describes why. Settle it with the full
  FinOps run, then retag. Issue #13.
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
