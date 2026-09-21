"""Golden dataset invariants — the seven rules from data-model.md §2."""

from __future__ import annotations

import collections

EXPECTED_DISTRIBUTION = {
    "grounded_happy": 10,
    "hallucinated_number": 5,
    "no_citation": 4,
    "missing_disclosure": 4,
    "stale_doc": 4,
    "pii_leak": 3,
}
REQUIRED_KEYS = {
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


def test_case_ids_are_unique_and_sequential(dataset):
    ids = [row["case_id"] for row in dataset]
    assert len(set(ids)) == len(ids), "duplicate case_id"
    assert ids == [f"MWP-{i:03d}" for i in range(1, len(dataset) + 1)]


def test_every_case_has_the_full_schema(dataset):
    for row in dataset:
        missing = REQUIRED_KEYS - set(row)
        assert not missing, f"{row.get('case_id')} missing keys: {missing}"


def test_tag_distribution_matches_the_spec(dataset):
    counts = collections.Counter(row["failure_tag"] for row in dataset)
    assert dict(counts) == EXPECTED_DISTRIBUTION


def test_total_case_count(dataset):
    assert len(dataset) == sum(EXPECTED_DISTRIBUTION.values()) == 30


def test_citations_resolve_to_real_documents(dataset, corpus_ids):
    for row in dataset:
        for field in ("expected_citations", "forbidden_citations"):
            for doc_id in row[field]:
                assert doc_id in corpus_ids, (
                    f"{row['case_id']} {field} references unknown document '{doc_id}'"
                )


def test_must_refuse_is_set_exactly_for_pii_cases(dataset):
    for row in dataset:
        expected = row["failure_tag"] == "pii_leak"
        assert row["must_refuse"] is expected, (
            f"{row['case_id']}: must_refuse should be {expected} for tag '{row['failure_tag']}'"
        )


def test_refusal_cases_expect_no_citations(dataset):
    """A refusal that cites a source has partially disclosed the source."""
    for row in dataset:
        if row["must_refuse"]:
            assert not row["expected_citations"], (
                f"{row['case_id']} must refuse, so it should expect no citations"
            )
            assert row["forbidden_phrases"], (
                f"{row['case_id']} must refuse but names nothing that would "
                "constitute a leak — the case cannot fail, so it proves nothing"
            )


def test_stale_doc_cases_forbid_the_superseded_schedule(dataset):
    for row in dataset:
        if row["failure_tag"] == "stale_doc":
            assert "meridian-fee-schedule-2025" in row["forbidden_citations"], (
                f"{row['case_id']} is a stale-doc case but does not forbid the superseded schedule"
            )
            assert "meridian-fee-schedule-2026" in row["expected_citations"]


def test_disclosure_cases_require_the_disclosure_sentence(dataset):
    for row in dataset:
        if row["failure_tag"] == "missing_disclosure":
            has_phrase = any(
                "Past performance does not guarantee" in phrase
                for phrase in row["required_phrases"]
            )
            cites_disclosures = "meridian-required-disclosures" in row["expected_citations"]
            assert has_phrase or cites_disclosures, (
                f"{row['case_id']} is a disclosure case but neither requires the "
                "disclosure sentence nor cites the disclosure document"
            )


def test_control_cases_exist_to_catch_over_refusal(dataset):
    """Hardening an agent until it refuses everything is not a win. The control
    cases are what make the v2 pass meaningful."""
    controls = [row for row in dataset if row["failure_tag"] == "grounded_happy"]
    assert len(controls) >= 10
    assert all(not row["must_refuse"] for row in controls)
