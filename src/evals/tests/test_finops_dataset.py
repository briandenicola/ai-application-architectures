"""FinOps golden dataset and rubric invariants.

The point of this file is one guard: **no figure in the dataset may contradict
the corpus**. A golden set whose expected answer disagrees with the documents
grades the agent against the harness's mistake, and it does so silently — the
agent reads the document, answers correctly, and is marked wrong. That failure
looks exactly like a model problem and will be debugged as one for a long time.

Everything else here is secondary.
"""

from __future__ import annotations

import re
import subprocess
import sys

import yaml
from conftest import FINOPS_DATASET, ROOT

# Fixed by deliberate design, not by accident. Both agents were probed against
# the live deployment first (docs/finops-trap-probe.md); the weight sits on
# synthesis failures because that is where the naive agent actually breaks.
# Changing a number here is a decision about what the demo claims, so make it
# on purpose.
EXPECTED_DISTRIBUTION = {
    "grounded_happy": 8,
    "stale_rate_card": 6,
    "fabricated_number": 5,
    "forecast_as_actual": 4,
    "unauthorized_recommendation": 3,
}

# Dropped 2026-09-23: metered_vs_billed, pii_leak and incident_vs_demand.
# Live probing showed v1 passed all six of those cases, so they carried no
# v1/v2 contrast while costing ~19% of every run. Every surviving tag is a
# synthesis failure, which is the only kind the probe showed actually fires.
DROPPED_TAGS = {"metered_vs_billed", "pii_leak", "incident_vs_demand"}

SCHEMA = {
    "case_id",
    "failure_tag",
    "query",
    "ground_truth",
    "expected_citations",
    "forbidden_citations",
    "required_phrases",
    "forbidden_phrases",
    "must_refuse",
    "notes",
}

# A phrase that looks like a money amount or a large count — the kind of thing
# that must be traceable to a document.
FIGURE = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$")


def test_total_case_count(finops_dataset):
    assert len(finops_dataset) == sum(EXPECTED_DISTRIBUTION.values()) == 26


def test_case_ids_are_unique_and_sequential(finops_dataset):
    ids = [case["case_id"] for case in finops_dataset]
    assert len(set(ids)) == len(ids), "duplicate case_id"
    assert ids == [f"MAP-{i:03d}" for i in range(1, len(ids) + 1)]


def test_every_case_has_the_full_schema(finops_dataset):
    for case in finops_dataset:
        assert set(case) == SCHEMA, f"{case['case_id']} has the wrong fields"


def test_tag_distribution_matches_the_spec(finops_dataset):
    from collections import Counter

    actual = Counter(case["failure_tag"] for case in finops_dataset)
    assert dict(actual) == EXPECTED_DISTRIBUTION


def test_citations_resolve_to_real_documents(finops_dataset, finops_ids):
    """A citation to a document that does not exist can never be satisfied."""
    for case in finops_dataset:
        for field in ("expected_citations", "forbidden_citations"):
            for doc_id in case[field]:
                assert doc_id in finops_ids, (
                    f"{case['case_id']} {field} names '{doc_id}', "
                    f"which is not a document in corpus-finops/"
                )


def test_every_expected_figure_appears_somewhere_in_the_corpus(finops_dataset, finops_docs):
    """The load-bearing guard.

    Every numeric `required_phrase` must be findable in the corpus. If it is
    not, the dataset is asking for a number the documents do not contain, and
    a correct agent will be graded wrong for refusing to invent it.
    """
    blob = "\n".join(finops_docs.values())
    for case in finops_dataset:
        for phrase in case["required_phrases"]:
            if not FIGURE.match(phrase):
                continue
            assert phrase in blob, (
                f"{case['case_id']} requires the figure '{phrase}', which appears "
                "in no FinOps document. Either the corpus changed and the dataset "
                "was not regenerated, or the expected answer is wrong."
            )


def test_refusal_cases_require_no_figures(finops_dataset):
    """A case whose correct answer is 'not published' cannot also demand a number."""
    for case in finops_dataset:
        if case["must_refuse"]:
            assert not case["required_phrases"], (
                f"{case['case_id']} must refuse but also requires "
                f"{case['required_phrases']} — those cannot both be satisfied."
            )
            assert not case["expected_citations"], (
                f"{case['case_id']} must refuse but expects citations"
            )


def test_dropped_tags_stay_dropped(finops_dataset):
    """Re-adding a dead trap should be a decision, not a drift."""
    present = {case["failure_tag"] for case in finops_dataset} & DROPPED_TAGS
    assert not present, (
        f"{sorted(present)} came back. These were dropped because v1 passed "
        "them — see docs/finops-trap-probe.md before re-adding."
    )


def test_contact_detail_protection_survived_dropping_the_pii_cases():
    """The PII cases went; the guard did not.

    Dropping MAP-030/031 removed the adversarial prompts that went looking for
    contact details. If the rubric dimension that actually grades leakage were
    also to stop applying everywhere, the track would silently lose PII
    protection altogether.
    """
    rubric = yaml.safe_load((ROOT / "evaluators" / "finops_defensible_answer.yaml").read_text())
    dims = {d["id"]: d for d in rubric["definition"]["dimensions"]}
    contact = dims.get("no_owner_contact_details")
    assert contact, "the rubric no longer grades owner contact details at all"
    assert contact["always_applicable"] is True, (
        "no_owner_contact_details must apply to every case now that no case "
        "specifically probes for a leak"
    )


def test_pii_forbidden_formats_are_really_in_the_registry(finops_docs):
    """...and the formats must actually be present, or the trap is hollow."""
    registry = finops_docs["meridian-ai-cost-center-registry"]
    assert "@example.com" in registry
    assert "555-01" in registry


def test_rate_card_cases_reference_both_cards_somewhere(finops_dataset):
    """The trap only exists if the dataset exercises both cards."""
    cases = [case for case in finops_dataset if case["failure_tag"] == "stale_rate_card"]
    cited = {doc for case in cases for doc in case["expected_citations"]}
    assert "meridian-model-rate-card-2025-10" in cited
    assert "meridian-model-rate-card-2026-01" in cited


def test_control_cases_exist_to_catch_over_refusal(finops_dataset):
    """Without controls, an agent that refuses everything scores perfectly on
    the traps. The grounded_happy cases are what make refusal costly."""
    controls = [case for case in finops_dataset if case["failure_tag"] == "grounded_happy"]
    assert len(controls) >= 8
    assert all(not case["must_refuse"] for case in controls)


def test_synthesis_cases_outweigh_refusal_cases(finops_dataset):
    """Encodes the probe's finding.

    Three of the six planted traps are handled by the model unaided, so cases
    that only test refusal no longer carry the v1/v2 contrast. If someone
    rebalances the set back toward them, the demo quietly stops demonstrating
    anything and this test says so.
    """
    synthesis = {
        "stale_rate_card",
        "fabricated_number",
        "forecast_as_actual",
        "unauthorized_recommendation",
    }
    refusal = DROPPED_TAGS
    n_synth = sum(1 for c in finops_dataset if c["failure_tag"] in synthesis)
    n_refusal = sum(1 for c in finops_dataset if c["failure_tag"] in refusal)
    assert n_synth >= 3 * n_refusal, (
        f"{n_synth} synthesis cases vs {n_refusal} refusal cases. The probe showed "
        "refusal traps do not discriminate between v1 and v2 — see "
        "docs/finops-trap-probe.md before rebalancing."
    )


def test_committed_dataset_is_current():
    """The dataset is generated from finops_data. If the corpus moves and the
    dataset does not, every figure in it becomes a guess."""
    result = subprocess.run(
        [sys.executable, "scripts/build_finops_golden.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{FINOPS_DATASET.name} is stale:\n{result.stdout}{result.stderr}"
    )
