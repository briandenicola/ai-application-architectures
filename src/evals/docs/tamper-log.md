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

## T9.3 — FinOps golden set and rubric (`tests/test_finops_dataset.py`, `tests/test_finops_rubric.py`)

The corpus guards protect the data; the parity guards protect the comparison.
These protect the **grader**. A dataset whose expected answer contradicts the
documents marks a correct agent wrong, and that failure is indistinguishable
from a model problem — it will be debugged as one, for a long time.

| Break | Test that caught it | Fired |
|---|---|---|
| Change a required figure to one that appears in no document | `test_every_expected_figure_appears_somewhere_in_the_corpus` | ✅ |
| Cite a document that does not exist | `test_citations_resolve_to_real_documents` | ✅ |
| Make a PII case forbid a format the registry never uses | `test_pii_cases_forbid_the_reserved_fiction_formats` | ✅ |
| Hand-edit the committed dataset instead of regenerating it | `test_committed_dataset_is_current` (+3 others) | ✅ |
| Cut `no_owner_contact_details` weight from 10 to 2 | `test_critical_dimensions_can_sink_a_case_alone` | ✅ |
| Replace `rate_card_in_effect` with the advisor rubric's `recency` | `test_it_is_not_a_copy_of_the_advisor_rubric` (+2) | ✅ |
| Make the fabrication dimension penalise omitting a figure | `test_the_figures_dimension_does_not_demand_figures` (+1) | ✅ |
| Point `custom_name` at a rubric nothing publishes | `test_config_points_at_this_rubric` | ✅ |

**One tamper was a silent no-op, and that is the entry worth reading.** The
first attempt at "make the fabrication dimension demand figures" passed,
because the replacement string spanned a line break in the YAML and matched
nothing. The file was never modified. The tamper reported green and proved
absolutely nothing — the same class of error as T2 in § T9.1, arriving by a
different route.

Two changes followed. Every tamper now asserts its substitution target exists
before writing, so a no-op fails loudly instead of masquerading as a passing
guard. And the test itself was tightened: it had read

```python
assert "must not be scored low" in text or "declining" in text
```

An `or` across two halves of one guarantee lets either half be deleted
silently. It now requires all three signals. The tamper that found this did so
only because its result was implausible — a guard that survives being deleted
is not a guard — which is the argument for reading tamper output rather than
scanning it for green.

**Why `no_fabricated_figures` needs this protection at all.** Three FinOps
cases have "not published" as the correct answer. If that dimension ever
penalises a response for omitting a number, those cases invert: the agent is
marked down for exactly the behaviour the rubric exists to produce, and the
hardened agent scores worse than the naive one. The rubric would still read
sensibly. The scorecard would be upside down.

## T10 — Exit-code contract and per-track metric resolution (2026-09-22)

Added after the **first live FinOps run crashed**. The suite was 135 tests green
and caught neither defect, because nothing exercised `run_eval.py` end to end on
a second track.

| # | Guard | Tamper | Result |
|---|---|---|---|
| T10.1 | `custom_metric()` reads the metric key from config | Re-hard-coded it to `"compliance_safe_answer"` | ✅ 2 failed — `test_custom_metric_is_resolved_per_track_not_hard_coded`, `test_every_tracks_custom_metric_is_actually_gated_on` |
| T10.2 | Unhandled exceptions exit 2, never 1 | Deleted the broad `except` in `__main__` | ✅ 1 failed — `test_a_harness_crash_exits_2_and_never_1` |
| T10.3 | Every track's custom metric has a threshold | Renamed `finops_defensible_answer` in `thresholds_finops` | ✅ 2 failed |

Every tamper asserted its target existed before writing, per § T9.3.

### What these two bugs actually were

**The metric key was a module constant pinned to the advisor track.** `--corpus
finops` swapped the dataset, evaluators and thresholds, but `CUSTOM_METRIC`
stayed `compliance_safe_answer`, so the FinOps run raised `KeyError` before
spending a token.

That was the lucky outcome. The two tracks happen to use different metric
names; had they shared one, there would have been no crash. The FinOps rubric
would have been **scored and gated against the advisor's threshold**, and the
run would have printed a complete, plausible, green scorecard for the wrong
contract. `test_every_tracks_custom_metric_is_actually_gated_on` is the guard
for the version of this bug that does not announce itself.

**The crash exited 1.** Constitution non-negotiable: `0` pass, `1` quality
threshold breached, `2` harness cannot run. Python exits 1 on an uncaught
exception, so *any* unhandled defect in the harness was reporting itself as a
failed quality gate. In CI that is a red build blamed on the model, and the
real fault is in the runner.

`ConfigError` was already routed to exit 2 — the contract was honoured for
anticipated failures and silently broken for every unanticipated one. Those are
the ones worth being right about.

### The lesson worth keeping

A `--corpus` flag that swaps config blocks looks like it makes a harness generic.
It does not. It makes the harness generic **only for the values that were
actually parameterised**, and a constant left behind is invisible until a second
track runs. The suite proved the swap worked for `dataset`, `evaluators` and
`thresholds`; nothing proved there was nothing else to swap.

Both of these were found by *running the thing*, not by reading it. 139 green
tests did not.

## T11 — Foundry owns every verdict (no local scoring)

The harness used to hold three private scoring paths: a `CUSTOM_PASS_SCORE = 0.9`
fallback, a local `score < thresholds[name]` comparison, and a locally computed
`verdict = all(m["pass"])`. Each could return a different answer than the portal
for the same run, with no way afterwards to say which number a customer had been
shown. All three are gone. Thresholds still exist, but only to be pushed into
Foundry testing criteria — never compared here.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T11.1 | No local fallback pass line | Reintroduced `CUSTOM_PASS_SCORE = 0.9` and used it when Foundry returned no verdict | ✅ `test_there_is_no_local_fallback_pass_line` failed |
| T11.2 | Verdict comes from Foundry's `result_counts` | Recomputed the verdict locally from per-case metrics | ✅ `test_the_verdict_comes_from_foundry_not_from_local_counting` failed |
| T11.3 | A missing verdict is an error, not a pass | Replaced the `evaluator_errors` record in `parse_case` with `passed = True` | ✅ `test_parse_case_records_a_missing_verdict_as_an_error_not_a_pass` failed |
| T11.4 | Absent `result_counts` exits 2 | Removed the guard entirely | ✅ `test_absent_result_counts_is_a_harness_failure` failed |

### Two guards were unproven on the first attempt

Worth recording, because both were ones I had already written a test for and
would otherwise have described as controls.

**T11.3 passed the tamper.** The test injected `evaluator_errors` into an
already-parsed case dict, so it exercised `summarise()` and never touched
`parse_case`. The guard it was named after had no coverage at all. Fixed by
driving `parse_case` with a real Foundry result payload containing a score but
no verdict.

**T11.4 passed the tamper.** Removing the absent-counts guard changed nothing
observable, because a downstream `total != len(cases)` check caught the empty
block and also exited 2. Defence in depth is good; a test that cannot tell which
of two guards fired is not. Fixed by asserting on the failure message, not only
the exit code.

### The lesson worth keeping

Asserting an exit code proves *something* refused. It does not prove **the guard
you named** refused. A test that passes through a redundant path is
indistinguishable from a test that works — until the day the redundant path is
also removed, and both guards turn out to have been one guard the whole time.
Tamper-test at the level the guard actually lives, and assert something only
that guard can produce.

---

## T12 — Coverage is part of the verdict

Found by finally letting a rehearsal run finish. A 3-case run over the 32-case
FinOps golden set printed a "Failures by staged failure mode" table listing all
eight modes, 32 cases, zero failures — then `GATE: PASS — cleared to ship`.
Twenty-nine of those cases had never been evaluated. The rollup was built by
iterating the dataset *file*, counting a case as present and marking it failed
only if an evaluated case of that id had failed. An unevaluated case therefore
rendered as a clean one.

This is the T7 threat in our own harness: the gate ran, printed a scorecard,
and reported clear.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T12.1 | Rollup counts evaluated cases only | Reverted to iterating the dataset file | ✅ `test_rollup_counts_only_cases_that_were_actually_evaluated` failed |
| T12.2 | Coverage reports the shortfall | Hard-coded `coverage["complete"] = True` | ✅ 2 tests failed |
| T12.3 | A partial pass is not a ship decision | Restored the unconditional "cleared to ship" banner | ✅ `test_a_partial_pass_is_not_described_as_cleared_to_ship` failed |

### The lesson worth keeping

Every number on that scorecard was true. The run did pass; those three cases
did clear every threshold; no evaluator errored. The table was assembled from
the dataset we *intended* to run rather than the cases Foundry *did* run, and
nothing in the output distinguished the two. A gate can mislead without
containing a single false statement — it only has to report on a different
population than the reader assumes.

So coverage is now a reported result, not a property of the invocation, and
the words "cleared to ship" are reserved for a run that evaluated everything.

---

## T13 — Dropping six cases must not quietly drop their protection

Six FinOps cases were removed after probing showed they never discriminated
between v1 and v2 (#10). The risk in deleting test cases is that the *guards*
attached to them leave with them, so the suite gets smaller and greener at the
same time — which looks like progress.

Two of the dropped tags carried protections that had to survive the deletion:
`pii_leak` was the only place contact-detail leakage was named, and
`metered_vs_billed` was the only place the two cost figures were contrasted.
Neither guard actually lived in the cases — `no_owner_contact_details` is
`always_applicable` at weight 10 — but nothing had ever demonstrated that.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T13.1 | Dropped tags stay dropped | Re-added a `metered_vs_billed` case to the builder | ✅ `test_dropped_tags_stay_dropped` failed |
| T13.2 | Contact-detail protection is universal | Set `no_owner_contact_details` to `always_applicable: false` | ✅ `test_contact_detail_protection_survived_dropping_the_pii_cases` failed |

Both tampers were run when the cases were dropped in `a324916`; this entry
records them. The log entry lagging the work is itself the failure mode this
document exists to prevent — an unrecorded tamper is indistinguishable from an
unrun one a week later.

---

## T14 — The HR track's traps are claims about the data

The HR dataset is not ours. Every trap in the track is a property of eight
CSVs that could be regenerated or swapped at any time, and each one would fail
silently: if the licence flag started genuinely partitioning users, the
"licensed vs unlicensed" comparison would stop being confounded and the demo
would quietly become a demonstration of nothing.

So the invariants are asserted rather than assumed, and the CSVs are
fingerprinted so that changing them is a deliberate act.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T14.1 | The licence flag does not gate usage | Made `unlicensed_rows_with_usage()` report 12/7335 instead of 7296/7335 | ✅ `test_the_licence_flag_does_not_gate_usage` failed |
| T14.2 | Synthetic data carries no routable address | Changed one employee's domain to `@gmail.com` | ✅ `test_employee_emails_use_a_single_non_routable_domain` **and** `test_source_csvs_have_not_changed` failed |
| T14.3 | Small cells exist to be suppressed | Lowered `SMALL_CELL_FLOOR` to 0 | ✅ `test_small_cells_exist_and_are_genuinely_small` failed |

T14.2 firing twice is the intended behaviour: the fingerprint catches *any*
edit to the source data, and the domain check explains *which* edit mattered.
A guard that only reports "something changed" sends you reading diffs; one
that only reports the domain would miss an edit elsewhere in the file.

### An open deviation, recorded rather than fixed

The constitution requires synthetic identifiers in reserved-for-fiction
formats — `@example.com` for email. These CSVs use `@techcorp.fake`, and
`.fake` is not reserved by RFC 2606. It is not currently delegated, so nothing
routes today, but that is a fact about the DNS root rather than a guarantee.
The test pins the domain so a genuinely routable address can never appear;
aligning the data with the constitution is tracked separately and was not done
unilaterally, because the data is the user's.

---

## T15 — The progress signal that caused #6

For weeks the harness reported that evaluation runs produced nothing. It read
`result_counts.total`, which is populated when a run *completes* and reads `0`
for the entire time one is in flight. We took that zero as evidence and
cancelled two healthy runs — one after 50 minutes, one after 5 that was
probably seconds from finishing. There was never a hang.

The fix reads `output_items`, which fills in per case. The guards exist to
stop the old reading returning.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T15.1 | Progress comes from `output_items` | Read `run["result_counts"]["total"]` instead | ✅ `test_progress_is_read_from_output_items_not_result_counts` failed |
| T15.2 | A failed probe is not zero progress | Made `scored_count` return `0` on exception | ✅ `test_a_failed_progress_probe_is_not_reported_as_zero_progress` failed — **on the second attempt**, see below |
| T15.3 | A stall is reported, never acted on | Made the stall branch call `fail()` | ✅ `test_a_stall_is_reported_but_never_cancels_the_run` failed |
| T15.4 | An unverifiable denominator is dropped | Kept trusting `expected_cases` after the run exceeded it | ✅ `test_an_untrustworthy_denominator_is_dropped_rather_than_shown` failed |

### T15.2 survived its first tamper, which means it was worthless

The original test asserted that `"scored 0"` never appeared in the output. It
passed with the guard removed, because with the guard removed the count is `0`
and the previous count is also `0`, so the "progress changed" branch never
fires and *nothing* is printed either way. The test was asserting the absence
of a string that was absent for an unrelated reason.

The real harm of swallowing a probe failure as `0` is that reported progress
goes **backwards** — a run that has scored 4 cases abruptly reports 0, which
reads as collapse. So the test now scores 4 cases first and only then starts
failing the probe. It fails under tamper.

This is the third guard this project has caught passing its own tamper (§T11
had two). The pattern is always the same: the assertion is true for a reason
other than the guard. Assert something **only the guard can produce**.

### Why a stall does not cancel

From the outside, a slow judge and a stuck run look identical. We have been
wrong about which we had twice, in the same direction, and both times the cost
was a cancelled run plus days of misdirected investigation. The harness now
says what it sees and keeps waiting. A human with the portal open can decide;
a 15-second poll loop cannot.

---

## T16 — A harness is generic only for the values actually parameterised

Both bugs fixed in `913d432` were found by *running* the harness against a
second corpus. 135 tests were green and caught neither. The suite had proved
that `--corpus` swapped the three blocks it knew about; nothing proved there
was nothing *else* that needed swapping, and a module constant still pinned to
the advisor track stayed invisible until a second track actually ran.

`tests/test_track_contract.py` walks the full path — criteria, metric
resolution, thresholds, parse, verdict — for every track **derived from
config** rather than a hard-coded pair. A hard-coded list would pass forever
while a new track went untested, which is the failure mode this replaces.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T16.1 | Every script's corpus registry agrees with config | Dropped `finops` from `index_corpus.CONFIG_SECTIONS` | ✅ `test_every_script_that_knows_about_corpora_knows_about_all_of_them` failed |
| T16.2 | Tracks do not share a rubric metric name | Set the FinOps `custom_metric` to `compliance_safe_answer` | ✅ `test_each_track_has_its_own_dataset_and_metric` failed (both params) |
| T16.3 | Tracks do not share a dataset | Pointed FinOps at `datasets/meridian-golden-v1.jsonl` | ✅ `test_each_track_has_its_own_dataset_and_metric` failed (both params) |
| T16.4 | Every track's gate can still say "fail" | Made `result_passed` return `True` for any boolean verdict | ✅ `test_a_failing_case_fails_the_gate_on_every_track` failed (both params) |

### Two tampers that had to be run twice

The first attempt at T16.2 hard-coded the metric inside `custom_metric`, and
the first attempt at T16.3 pointed a track at a path that did not exist. Both
produced red suites, and both were **worthless as evidence**: they crashed in
`check_thresholds` and in the dataset-existence check respectively, before
reaching the uniqueness guards they were meant to exercise.

A red suite is not proof that the guard you named did the catching. Check
*which* test failed, not merely that one did — the same mistake as §T11, in a
new costume.

### Why T16.2 is the one that matters

The FinOps run died on a `KeyError` before spending a token, which is the one
harmless way that bug could surface. Had the two rubrics happened to share a
metric name, the FinOps gate would have been judged against the advisor's
threshold and printed a full, plausible, green scorecard for the wrong rubric.
That near-miss is now a test.

### A registry problem this surfaced

`--corpus` is not one switch. `select_corpus` swaps dataset/evaluators/
thresholds, `index_corpus` maps a track to a knowledge block, and
`create_agents` maps it to an agents block. Three registries, edited by hand,
and until now nothing checked they agreed — a track registered in config but
missing from `create_agents` would fail at demo time rather than test time.
With the HR track about to be added, that was a scheduled failure.

---

## T17 — A corpus that commits the violation it tests for

The HR track grades an agent on disclosure discipline. That only works if the
corpus itself is disciplined. If a document publishes an individual's figures,
an agent repeating them is **grounded** — it would be graded correct, and the
track would be measuring the corpus rather than the agent.

The first two drafts of `generate_hr_corpus.py` both failed this.

**Draft 1** published the Executive department in all twelve monthly reports.
Executive is one person: the chief executive. Every figure under that label —
query counts, estimated hours saved, licensed share — was his individual
record, published twelve times.

**Draft 2** suppressed small cells in a department-by-level headcount grid and
published the row totals beside them. Human Resources' visible cells summed to
323 against a published total of 324, so the withheld Director cell was
exactly 1. The suppression was decorative; the arithmetic gave it straight
back. Data & Analytics leaked almost as badly.

| # | Guard | Tamper applied | Result |
|---|---|---|---|
| T17.1 | No sub-floor department is ever reported | Set `SMALL_DEPARTMENTS = ()` | ✅ `test_no_department_below_the_floor_is_ever_reported` and `test_no_published_group_size_is_below_the_floor` failed |
| T17.2 | Seniority is banded above the floor | Split the bands back into raw levels (C-Suite n=1, VP n=2) | ✅ `test_no_published_group_size_is_below_the_floor` and `test_every_band_clears_the_floor` failed |
| T17.3 | The estimate is reconciled against measured hours | Replaced the 175.31/174.73 comparison with "Withheld" | ✅ `test_the_methodology_reconciles_the_estimate_against_measured_hours` failed — **on the second attempt**, see below |
| T17.4 | The committed corpus matches the generator | Hand-edited a heading in the annual summary | ✅ `test_committed_corpus_matches_the_generator` failed |
| T17.5 | The policy prohibits defeating suppression by arithmetic | Replaced clause 2a with "Reserved for future use" | ✅ `test_the_policy_prohibits_defeating_suppression_by_arithmetic` failed |

### T17.3's first attempt did not apply at all

The tamper script asserted its search string was present, replaced it, and
reported success. The suite stayed green, which read as an unproven guard.

It was not. `ruff format` had reindented the expression inside the f-string, so
the *second* replacement in the script silently matched nothing while the first
succeeded. The generated document still contained 175.31 and the test was
correctly passing on unmodified output.

Two lessons, and the second is the one that generalises. First: assert on the
*effect* of a tamper, not just the edit — the retry greps the generated
document for `175.31` and confirms it is gone before trusting the result.
Second: a tamper that fails to apply and a guard that fails to fire look
identical from the test output. This is the same class of mistake as §T15.2 and
§T16, arriving in a third costume.

### The residual that was kept on purpose

Executive is withheld from every department breakdown, but firm-wide totals are
published across the corpus, so subtracting the published rows still yields the
chief executive's figures. That hole was not closed. It was documented instead:
governance clause 2a prohibits reconstructing a suppressed group by
subtraction or differencing.

This is deliberate. Mathematically eliminating residual disclosure would mean
suppressing totals across twenty-two documents and would remove the most
interesting question in the track. Leaving it, and stating the rule, converts
it into a gradeable test: an agent that performs the subtraction is violating a
policy it retrieved, not being resourceful.

A control that a determined reader can defeat is still a control, provided the
rule is explicit and the failure is detectable. Pretending otherwise would be
the real dishonesty.

## T18 — The HR agent pair (`tests/test_hr_agent_parity.py`)

Third v1/v2 pair, and the first where both versions can state every figure
correctly and only one of them is safe. The parity contract matters more here
than in the other two tracks, because the claim under test is subtler: not
"v2 gets the numbers right" but "v2 declines to draw a conclusion the numbers
cannot support". If v2 quietly received a stronger model, that claim would be
unfalsifiable rather than false, which is worse.

| # | Tamper | Expected | Test that failed | Result |
|---|--------|----------|------------------|--------|
| T18.1 | Gave v2 deployment `gpt-5.5-turbo-better` | parity breach | `test_models_are_identical`, `test_only_permitted_fields_differ` | ✅ caught |
| T18.2 | Removed **both** mentions of "no control group" from v2 GUARD 3 | causal guard degrades to etiquette | `test_v2_causal_guard_names_why_the_data_cannot_support_causation` | ✅ caught |
| T18.3 | Changed v1's "answer for that team" to "answer for the whole company" | small-group trap never fires | `test_v1_actively_invites_the_planted_failures` | ✅ caught |
| T18.4 | Pointed v1 at `${AZURE_SEARCH_FINOPS_INDEX}` | agents ground on different corpora | `test_both_agents_use_the_same_index`, `test_both_ground_against_the_hr_corpus` | ✅ caught |

All four green after revert; `diff` against a pre-tamper copy confirmed both
files were restored byte-for-byte before the final run.

### T18.2 failed to prove anything on the first attempt

The first attempt replaced the sentence "There is no control group." and the
suite stayed green. The guard looked unproven.

It was not. `grep` showed the phrase still present on another line: GUARD 3
names the defect twice, once as a statement of fact and once in the list of
reasons the agent must give when declining. The assertion is over the
flattened instruction text, so the second mention satisfied it. The tamper had
removed a sentence but not the property being asserted.

Removing both mentions failed the test immediately, and named the right one.

This is the fourth time this project has run a tamper that proved nothing, and
the fourth distinct disguise:

- §T11 — the assertion was true for an unrelated reason.
- §T15.2 — asserted a string was absent; it was absent either way.
- §T16 — the tamper crashed before reaching the guard it targeted.
- §T18.2 — the tamper removed one instance of a phrase that appeared twice.

The countermeasure is the same every time and it is not "tamper harder": after
each tamper, verify the property you intended to destroy is actually gone
before reading the test result. Here that was one `grep -c`, which took a
second and turned a false negative into a proven guard.

### T18.3 is the one that protects the demo

A guard with no matching temptation is decoration. v1 must be *tempted* into
each failure by an instruction a reasonable person would write and a prompt
review would wave through — "answer the question that was actually asked", "say
what is driving it", "use our best measure of value". Each maps to exactly one
v2 guard.

If a temptation is softened, v1 may behave well by accident, the trap never
fires, and the gate passes an agent nobody proved anything about. T18.3
confirms that softening one is caught. A green gate in that state is the single
most expensive failure mode this project has, because it looks exactly like
success.

---

> If a row in this log is empty, the corresponding guard is **unproven**. Do not
> describe it as a control in front of a client.
