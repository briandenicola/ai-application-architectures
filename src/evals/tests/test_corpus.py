"""Corpus invariants.

The demo plants realistic-looking PII on purpose. These tests are what keep that
decision safe: every identifier must use a format reserved for fiction, and every
document must carry a banner that survives being screenshotted.
"""

from __future__ import annotations

import re

import pytest
import yaml
from conftest import EXPECTED_DOCUMENT_COUNT

BANNER_WINDOW = 400
REQUIRED_FRONT_MATTER = {
    "title",
    "doc_id",
    "doc_type",
    "effective_date",
    "supersedes",
    "status",
    "contains_pii",
    "owner",
}
VALID_TYPES = {"factsheet", "fee_schedule", "policy", "disclosure", "ips", "reference"}
VALID_STATUS = {"current", "superseded"}


def front_matter(path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name} has no YAML front matter"
    _, raw, _ = text.split("---", 2)
    return yaml.safe_load(raw)


def test_corpus_has_expected_document_count(corpus_paths):
    assert len(corpus_paths) == EXPECTED_DOCUMENT_COUNT


def test_every_document_carries_the_synthetic_banner(corpus_paths):
    for path in corpus_paths:
        head = path.read_text(encoding="utf-8")[:BANNER_WINDOW]
        assert "SYNTHETIC" in head, (
            f"{path.name} lacks the SYNTHETIC banner in its first {BANNER_WINDOW} "
            "characters. A screenshot of this document could be mistaken for client data."
        )


def test_front_matter_is_complete_and_valid(corpus_paths):
    for path in corpus_paths:
        meta = front_matter(path)
        missing = REQUIRED_FRONT_MATTER - set(meta)
        assert not missing, f"{path.name} missing front matter keys: {missing}"
        assert meta["doc_id"] == path.stem, f"{path.name}: doc_id must match filename"
        assert meta["doc_type"] in VALID_TYPES, f"{path.name}: bad doc_type {meta['doc_type']}"
        assert meta["status"] in VALID_STATUS, f"{path.name}: bad status {meta['status']}"


def test_supersedes_references_resolve(corpus_paths, corpus_ids):
    for path in corpus_paths:
        meta = front_matter(path)
        target = meta.get("supersedes")
        if target:
            assert target in corpus_ids, f"{path.name} supersedes unknown doc '{target}'"


def test_stale_doc_trap_is_present_and_contradictory(corpus_paths):
    """The stale-document story only works if the two schedules actually disagree."""
    current = next(p for p in corpus_paths if p.stem == "meridian-fee-schedule-2026")
    superseded = next(p for p in corpus_paths if p.stem == "meridian-fee-schedule-2025")

    assert front_matter(superseded)["status"] == "superseded"
    assert front_matter(current)["supersedes"] == "meridian-fee-schedule-2025"

    old = superseded.read_text(encoding="utf-8")
    new = current.read_text(encoding="utf-8")

    # Every tier rate must differ between the two schedules.
    contradictions = [
        ("1.15%", "1.00%"),
        ("0.85%", "0.65%"),
        ("0.70%", "0.50%"),
        ("0.50%", "0.35%"),
        ("$7,500", "$5,000"),
    ]
    for old_value, new_value in contradictions:
        assert old_value in old, f"superseded schedule missing {old_value}"
        assert new_value in new, f"current schedule missing {new_value}"


def test_exactly_one_document_declares_pii(corpus_paths):
    flagged = [p.stem for p in corpus_paths if front_matter(p)["contains_pii"]]
    assert flagged == ["meridian-ips-client-aa1042"], (
        f"Expected exactly one PII document, found {flagged}. "
        "Unflagged PII would escape the handling rules."
    )


@pytest.mark.parametrize(
    ("label", "pattern", "reserved"),
    [
        # Any SSN-shaped string must use the never-issued 000 area number.
        ("SSN", r"\b(\d{3})-(\d{2})-(\d{4})\b", lambda m: m.group(1) == "000"),
        # Any US phone number must sit in the 555-01xx fiction block.
        (
            "phone",
            r"\(\d{3}\)\s*(\d{3})-(\d{4})\b",
            lambda m: m.group(1) == "555" and m.group(2).startswith("01"),
        ),
        # Any email must use an RFC 2606 reserved domain.
        (
            "email",
            r"\b[\w.+-]+@([\w.-]+\.\w+)\b",
            lambda m: m.group(1).endswith(("example.com", "example.org", "example.net")),
        ),
    ],
)
def test_identifiers_use_reserved_fiction_formats(corpus_paths, label, pattern, reserved):
    for path in corpus_paths:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(pattern, text):
            assert reserved(match), (
                f"{path.name} contains a {label} outside the reserved-for-fiction "
                f"range: {match.group(0)!r}. Synthetic data must be unmistakably synthetic."
            )


def test_pii_document_explains_why_it_exists(corpus_paths):
    """A planted-PII file without a rationale is indistinguishable from a mistake."""
    path = next(p for p in corpus_paths if p.stem == "meridian-ips-client-aa1042")
    text = path.read_text(encoding="utf-8")
    assert "Why this document exists" in text
    assert "does not exist" in text
