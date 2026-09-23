"""HR golden dataset invariants.

The dataset is generated, so these tests are not guarding against typos. They
guard against the two ways a generated dataset still goes wrong:

1. It asserts something the corpus does not contain, so a correct agent fails.
2. It asserts something no agent can produce, so an incorrect agent passes.

The second is worse and harder to see. `tests/test_gate.py` covers the gate;
this file covers whether the cases it grades mean anything.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DATASET = ROOT / "datasets" / "meridian-hr-golden-v1.jsonl"
BUILDER = ROOT / "scripts" / "build_hr_golden.py"
CORPUS = ROOT / "corpus-hr"

# Round 1 fired 4 of 12; round 2 fired 9 of 9. The mix below reflects that and
# is deliberate, not incidental. Changing it means re-reading docs/hr-traps.md
# and deciding to change it.
EXPECTED_TAGS = {
    "fabricated_figure": 6,
    "grounded_happy": 5,
    "causal_overreach": 4,
    "individual_or_small_n": 3,
    "unauthorized_recommendation": 3,
    "unlabelled_estimate": 2,
    "population_error": 2,
}


def cases() -> list[dict]:
    with DATASET.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@pytest.fixture(scope="module")
def corpus_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(CORPUS.glob("*.md")))


def test_dataset_exists_and_is_not_empty():
    assert DATASET.exists(), "run scripts/build_hr_golden.py"
    assert cases()


def test_committed_dataset_matches_the_generator():
    """A hand-edited dataset drifts from the corpus silently."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user input
        [sys.executable, str(BUILDER), "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_case_ids_are_unique():
    ids = [c["case_id"] for c in cases()]
    assert len(ids) == len(set(ids))


def test_tag_distribution_is_deliberate():
    import collections

    actual = dict(collections.Counter(c["failure_tag"] for c in cases()))
    assert actual == EXPECTED_TAGS, (
        f"tag mix changed: {actual}. The weighting comes from two probe rounds "
        "(docs/hr-traps.md) — round 1 fired 4 of 12 because the corpus answers "
        "its own caveats, round 2 fired 9 of 9 because it asks for what the "
        "corpus lacks. Update this only alongside that reasoning."
    )


def test_every_case_has_a_query_and_ground_truth():
    for c in cases():
        assert c["query"].strip(), c["case_id"]
        assert c["ground_truth"].strip(), c["case_id"]
        assert c["notes"].strip(), f"{c['case_id']} must record why it exists"


def test_no_case_asserts_citations_while_issue_14_is_open():
    """Two defects sit under #14, and the second is the worse one.

    First: no agent on this deployment emits a real doc_id. It cites doc_type
    values and content_hash strings, because doc_id is the index key and never
    reaches the model.

    Second, and only established after the first was filed: nothing in the
    scoring path reads a citation field at all. Every data_mapping built by
    `run_eval.build_testing_criteria` carries query, response and — for
    groundedness — context. So an expected_citations assertion would not fail
    for every agent; it would simply never be evaluated, and a
    forbidden_citations assertion passes for every agent forever. A check that
    cannot trip is indistinguishable from a check that passed.

    `test_no_evaluator_consumes_the_citation_fields` in test_track_contract.py
    pins that second defect across every registered track. This test keeps the
    HR golden set out of the trap in the meantime.

    When #14 is fixed, delete this test and add the citation expectations
    deliberately — do not let them creep back in one case at a time.
    """
    for c in cases():
        assert c["expected_citations"] == [], c["case_id"]
        assert c["forbidden_citations"] == [], c["case_id"]


def test_required_phrases_actually_appear_in_the_corpus(corpus_text):
    """A required phrase absent from every document is unanswerable.

    This is the failure that makes a golden set grade the harness rather than
    the agent, and it is invisible until a well-behaved agent starts failing.
    """
    numeric = []
    for c in cases():
        for phrase in c["required_phrases"]:
            if any(ch.isdigit() for ch in phrase):
                numeric.append((c["case_id"], phrase))

    missing = [(cid, p) for cid, p in numeric if p not in corpus_text]
    assert not missing, (
        f"required phrases not present anywhere in corpus-hr: {missing}. "
        "Either the figure is wrong or the corpus does not publish it."
    )


def test_refusal_cases_do_not_require_numeric_phrases():
    """Asking an agent to refuse and to state a figure at the same time is a
    contradictory case, and whichever way it answers, the result is noise."""
    for c in cases():
        if not c["must_refuse"]:
            continue
        numeric = [p for p in c["required_phrases"] if any(ch.isdigit() for ch in p)]
        assert not numeric, f"{c['case_id']} demands refusal and a number: {numeric}"


def test_control_cases_are_not_refusals():
    for c in cases():
        if c["failure_tag"] == "grounded_happy":
            assert not c["must_refuse"], f"{c['case_id']} is a control; it must be answerable"


def test_forbidden_phrases_are_not_also_required():
    for c in cases():
        overlap = set(c["required_phrases"]) & set(c["forbidden_phrases"])
        assert not overlap, f"{c['case_id']} both requires and forbids {overlap}"


def test_the_probe_evidence_is_represented():
    """Every case says where its expected behaviour came from.

    Three legitimate answers: it was observed in round 1, observed in round 2,
    or is a control whose provenance is the corpus rather than an agent. A
    fourth — silence — means the case was written against an assumption.

    The FinOps set was written against assumed behaviour and lost six cases
    when the assumptions were finally checked. This keeps the provenance
    attached to the case rather than to a document someone may not read.
    """
    markers = ("round 1", "round 2", "not probed", "control")
    for c in cases():
        notes = c["notes"].lower()
        assert any(m in notes for m in markers), (
            f"{c['case_id']} does not say whether its behaviour was observed, "
            f"assumed, or derived from the corpus"
        )


def test_the_demo_case_is_present():
    """MHR-061 is the single answer containing four distinct failures. If it is
    ever dropped, the track loses its strongest moment."""
    ids = {c["case_id"] for c in cases()}
    assert "MHR-061" in ids
    assert "MHR-010" in ids, "the '0.23 hours/week' case is the clearest in the set"


def test_dataset_is_not_registered_in_config_before_the_rubric_exists():
    """dataset_hr activates tests/test_track_contract.py, which will then
    require evaluators_hr and thresholds_hr. Registering early turns a green
    suite into a statement about nothing."""
    import yaml

    with (ROOT / "evals.config.yaml").open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if "dataset_hr" in config:
        assert "evaluators_hr" in config and "thresholds_hr" in config, (
            "dataset_hr is registered but the rubric or thresholds are missing — "
            "the HR track would be evaluated against an incomplete contract"
        )
