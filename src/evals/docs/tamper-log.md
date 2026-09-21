# Tamper Log

The constitution requires that every guard be observed failing before it is
trusted. A guard that has never been seen to fail is an assumption wearing a
guard's uniform.

**Procedure.** Break the guard → run the check → confirm it fails → revert →
confirm green. Record the result here.

| Date | Guard / invariant | How it was broken | Expected signal | Observed | Reverted |
|------|-------------------|-------------------|-----------------|----------|----------|
| 2026-09-21 | **Quality gate blocks** (`run_eval.summarise`) | Forced `"pass": True` regardless of threshold | Gate tests fail | ✅ `test_a_single_breached_metric_fails_the_whole_gate` and `test_exit_code_tracks_verdict_exactly` failed (`assert 0 == 1`) | ✅ 35/35 green |
| | | | | | |

## Outstanding — Phase 8

These require a deployed environment (T8.1). Run them once, record the result,
and never take them on faith again.

### T8.1 — the five v2 guards

For each, remove the guard from `agents/v2-hardened.agent.yaml`, run
`python scripts/create_agents.py && python scripts/run_eval.py --agent meridian-advisor-v2`,
confirm the expected metric flips to fail, then revert.

| Guard | Remove | Expected to break |
|-------|--------|-------------------|
| 1 — Grounding | The "never state a figure" paragraph | Groundedness drops below 4.0; MWP-015 produces a fabricated percentage |
| 2 — Citation | The citation-format paragraph + set `include_citations: false` | `compliance_safe_answer` criterion 2 fails on MWP-016 … MWP-019 |
| 3 — Recency | The effective-date paragraph | MWP-024 … MWP-027 quote the superseded schedule; Retrieval drops |
| 4 — Disclosure | The required-disclosure paragraph | `compliance_safe_answer` criterion 3 fails on MWP-020 … MWP-023 |
| 5 — Boundaries | The PII / no-advice paragraph | MWP-028 … MWP-030 leak; Task Adherence drops |

Note also: `tests/test_agent_parity.py::test_v2_contains_all_five_guards` should
fail the moment a guard heading is removed. That is a second, cheaper signal —
confirm it fires too.

### T8.2 — dataset invariants

| Break | Expected |
|-------|----------|
| Change a `case_id` to a duplicate | `test_case_ids_are_unique_and_sequential` |
| Retag one case | `test_tag_distribution_matches_the_spec` |
| Point `expected_citations` at a nonexistent doc | `test_citations_resolve_to_real_documents` |
| Set `must_refuse: true` on a non-PII case | `test_must_refuse_is_set_exactly_for_pii_cases` |

### T8.3 — corpus invariants

| Break | Expected |
|-------|----------|
| Remove the SYNTHETIC banner from one document | `test_every_document_carries_the_synthetic_banner` |
| Change the SSN to a real-format area number (e.g. `123-45-6789`) | `test_identifiers_use_reserved_fiction_formats` |
| Align the two fee schedules so they agree | `test_stale_doc_trap_is_present_and_contradictory` |
| Set `contains_pii: false` on the IPS document | `test_exactly_one_document_declares_pii` |

### T8.4 — the knowledge post-conditions

| Break | Expected |
|-------|----------|
| Delete one document from the index, re-run `setup_knowledge.py` | Exits non-zero: indexed count ≠ 12 |
| Set `reranker_threshold` high enough to drop the fee schedules | Canary fails, exits non-zero |


### T8.5 — the evaluation harness itself

Added after a live 30-case run reported `pii_leak` as **0 failures** when the
compliance rubric had in fact errored on 2 of those 3 cases and been averaged
away. Verified 2026-09-21.

| Break | Expected | Verified |
|-------|----------|----------|
| Set `always_applicable: true` on `attributed_figures` | `test_always_applicable_dimensions_never_declare_an_inapplicable_case` | ✅ failed, then passed on revert |
| Delete the errored-result guard from `summarise()` | `test_errored_evaluator_results_fail_the_harness` | ✅ failed, then passed on revert |
| Let a metric score fewer cases than the dataset holds | `test_partial_scoring_fails_the_harness` | ✅ |
| Set `task_adherence` threshold to 4.0 (off-scale) | `test_unreachable_threshold_is_rejected` | ✅ |
| Re-add `retrieval` to the evaluator list | `test_retrieval_is_not_configured` | ✅ |

---

> If a row in this log is empty, the corresponding guard is **unproven**. Do not
> describe it as a control in front of a client.
