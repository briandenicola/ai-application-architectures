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
| Set a threshold off its metric's scale | `test_unreachable_threshold_is_rejected` | ✅ |
| Re-add `task_adherence` to the evaluator list | `test_task_adherence_is_not_configured`, `test_no_evaluator_punishes_a_correct_refusal` | ✅ failed, then passed on revert |
| Re-add `retrieval` to the evaluator list | `test_retrieval_is_not_configured` | ✅ |

### T8.6 — the corpus must not defeat its own trap

Added after discovering that none of the three planted traps fired against
`gpt-5.5`. The stale document announced its own obsolescence in its body, and the
current document listed every superseded rate beside its replacement — so
retrieving the wrong schedule cost nothing. Verified 2026-09-21.

| Break | Expected | Verified |
|-------|----------|----------|
| Re-add `(reduced from $7,500)` to the 2026 schedule | `test_fee_schedules_do_not_defeat_their_own_trap` | ✅ failed, then passed on revert |
| Restore the "THIS SCHEDULE IS SUPERSEDED / do not quote" banner to the 2025 schedule | `test_fee_schedules_do_not_defeat_their_own_trap` | ✅ |

### T9.1 — the FinOps corpus (`corpus-finops/`)

The FinOps corpus is *generated* from `scripts/finops_data.py`, so its guards
protect something the advisor corpus does not need: arithmetic. Roughly 240
usage rows must reconcile across nineteen documents, three roll-up axes and two
rate cards. All eight breaks below were performed, observed, and reverted on
2026-09-22.

| Break | Expected signal | Observed |
|-------|-----------------|----------|
| Alter one metered cost cell in the February statement | `test_bu_detail_tables_add_up`, `test_detail_rows_reprice_from_the_stated_rate_card` | ✅ both failed, green on revert |
| Pin every month to the January 2026 rate card | `test_statements_price_against_the_card_in_effect`, `test_detail_rows_reprice_from_the_stated_rate_card` | ✅ failed for all three 2025 months |
| Delete the ITD February breach row from the summary | `test_declared_breaches_are_exactly_the_real_breaches` | ✅ |
| Append "these rates are superseded" to the October card | `test_superseded_rate_card_does_not_announce_its_own_obsolescence` | ✅ |
| Give a cost-centre owner a real-format phone number | `test_identifiers_use_reserved_fiction_formats[phone]` | ✅ |
| Apply the platform uplift to the aggregate rather than per cost centre | `test_month_summary_matches_detail_and_applies_the_uplift` | ✅ failed for every month |
| Change one summary-matrix cell so it disagrees with its statement | `test_summary_matrix_ties_to_every_monthly_statement` | ✅ |
| Remove the SYNTHETIC banner from every document | `test_every_document_carries_the_synthetic_banner` | ✅ |

**One tamper test changed the design.** The first attempt at
"pin every month to the January card" **passed**, because
`test_detail_rows_reprice_from_the_stated_rate_card` recomputed costs with
`cost_for()`, which calls the same `rate_card_for()` the test was meant to
validate. The corpus regenerated at the wrong prices and the test agreed with
the bug. The test now parses the rates out of the rate-card *document* named by
the statement, and the month-to-card mapping is asserted against a literal
table in the test module rather than derived from the code under test. This is
the whole argument for tamper testing: the guard was green, looked reasonable,
and checked nothing.

## T9.2 — FinOps agent parity (`tests/test_finops_agent_parity.py`)

The corpus guards protect the *data*. These protect the *comparison*. A demo
that claims "the same model, the same corpus, a better prompt" is only worth
showing if something enforces the "same model, same corpus" half.

| Break | Test that caught it | Fired |
|---|---|---|
| Bump v2's model version so it silently runs a newer model than v1 | `test_models_are_identical`, `test_only_permitted_fields_differ` | ✅ |
| Point v2 at the advisor index instead of the FinOps one | `test_both_agents_use_the_same_index`, `test_both_ground_against_the_finops_corpus_not_the_advisor_one` | ✅ |
| Soften GUARD 3 into a generic "always prefer the newest document" rule | `test_v2_contains_all_seven_guards`, `test_v2_recency_guard_is_period_based_not_latest_based` | ✅ |
| Add "always cite the document you used" to v1 | `test_v1_is_genuinely_ungoverned` | ✅ |
| Remove v1's "quote our current prices" temptation | `test_v1_actively_invites_the_planted_failures` | ✅ |

**Why the third break matters more than it looks.** In the advisor demo,
"prefer the most recent document" is the *correct* rule — the current fee
schedule always wins. In a cost corpus it is the *bug*: the superseded
`meridian-model-rate-card-2025-10` is the rightful authority for the three
months it covers, and an agent that reaches for the newest card silently
reprices a closed billing period. A guard copied across from the advisor agent
would read as sensible, pass review, and cause the exact failure the corpus was
built to catch. `test_v2_recency_guard_is_period_based_not_latest_based` exists
to stop that copy-paste, and it names both card IDs so the rule cannot decay
into a vague appeal to recency.

**Why v1 is tempted rather than merely unguarded.** An agent with no
instructions at all would be ungoverned, but it might behave anyway, and then
the demo rests on luck. `test_v1_actively_invites_the_planted_failures` pins
five ordinary-sounding productivity asks in v1's prompt, each steering it into
one planted trap. A trap that never fires proves nothing about the guard that
would have caught it.

---

> If a row in this log is empty, the corresponding guard is **unproven**. Do not
> describe it as a control in front of a client.
