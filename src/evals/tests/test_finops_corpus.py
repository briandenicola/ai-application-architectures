"""FinOps corpus invariants.

These tests read the *rendered markdown*, not the generator's in-memory model.
That distinction is the whole point: a test that asks the generator whether the
generator is right proves nothing. Everything here is parsed back out of the
committed documents and re-added, so a renderer bug that drops a row or formats
a column wrong fails here rather than on stage.

The corpus makes a specific claim — that an agent which gets the arithmetic
wrong, prices a period against the wrong rate card, or confuses metered with
billed cost is *demonstrably* wrong. That claim is only defensible if the
documents themselves reconcile.
"""

from __future__ import annotations

import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
import yaml
from conftest import EXPECTED_FINOPS_DOCUMENT_COUNT, FINOPS_CORPUS_DIR, ROOT
from finops_data import (
    ANOMALY_BU,
    ANOMALY_MONTH,
    BUSINESS_UNITS,
    MODEL_NAMES,
    MONTHS,
    PLATFORM_UPLIFT,
    RATE_CARD_2025_10,
    RATE_CARD_2026_01,
    rate_card_for,
)

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
VALID_TYPES = {
    "rate_card",
    "usage_statement",
    "summary",
    "incident",
    "forecast",
    "policy",
    "registry",
    "reference",
    "disclosure",
}
VALID_STATUS = {"current", "superseded"}

# Stated here as a literal rather than derived from `rate_card_for`, so this
# test suite still fails if the rule that picks a card is broken.
EXPECTED_RATE_CARD = {
    "2025-10": "meridian-model-rate-card-2025-10",
    "2025-11": "meridian-model-rate-card-2025-10",
    "2025-12": "meridian-model-rate-card-2025-10",
    "2026-01": "meridian-model-rate-card-2026-01",
    "2026-02": "meridian-model-rate-card-2026-01",
    "2026-03": "meridian-model-rate-card-2026-01",
}

PII_DOC = "meridian-ai-cost-center-registry"
SUMMARY_DOC = "meridian-ai-cost-summary-fy26h1"
BU_CODES = [bu.code for bu in BUSINESS_UNITS]


# ── parsing ──────────────────────────────────────────────────────────────────


def front_matter(text: str) -> dict:
    assert text.startswith("---"), "document has no YAML front matter"
    _, raw, _ = text.split("---", 2)
    return yaml.safe_load(raw)


def clean(cell: str) -> str:
    return cell.replace("**", "").replace("`", "").strip()


def _body(text: str) -> str:
    """Prose only. The front matter is *where recency is supposed to live*, so a
    check for self-announced obsolescence must not read it."""
    _, _, body = text.split("---", 2)
    return body


def money(cell: str) -> Decimal:
    value = clean(cell).replace("$", "").replace(",", "")
    if value.startswith("+"):
        value = value[1:]
    return Decimal(value)


def count(cell: str) -> int:
    return int(clean(cell).replace(",", ""))


def tables(text: str) -> list[list[list[str]]]:
    """Every markdown table in the document, as a list of cell rows.

    The separator row is dropped; the header row is kept as row 0.
    """
    found: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            current.append(cells)
        elif current:
            found.append(current)
            current = []
    if current:
        found.append(current)
    return found


def table_after(text: str, heading: str) -> list[list[str]]:
    """The first table following a given markdown heading."""
    index = text.index(heading)
    section = text[index:]
    found = tables(section)
    assert found, f"no table after heading {heading!r}"
    return found[0]


MATRIX_HEADING = "## Billed cost by business unit and month"


def summary_matrix(finops_docs: dict) -> list[list[str]]:
    return table_after(finops_docs[SUMMARY_DOC], MATRIX_HEADING)


def summary_matrix_by_bu(finops_docs: dict) -> dict[str, list[str]]:
    return {clean(row[0]): row for row in summary_matrix(finops_docs)[1:-1]}


# ── structural invariants ────────────────────────────────────────────────────


def test_corpus_has_expected_document_count(finops_paths):
    assert len(finops_paths) == EXPECTED_FINOPS_DOCUMENT_COUNT


def test_every_document_carries_the_synthetic_banner(finops_paths):
    for path in finops_paths:
        head = path.read_text(encoding="utf-8")[:BANNER_WINDOW]
        assert "SYNTHETIC" in head, (
            f"{path.name} lacks the SYNTHETIC banner in its first {BANNER_WINDOW} "
            "characters. A screenshot of this document could be mistaken for real "
            "cost data."
        )


def test_front_matter_is_complete_and_valid(finops_paths):
    for path in finops_paths:
        meta = front_matter(path.read_text(encoding="utf-8"))
        missing = REQUIRED_FRONT_MATTER - set(meta)
        assert not missing, f"{path.name} missing front matter keys: {missing}"
        assert meta["doc_id"] == path.stem, f"{path.name}: doc_id must match filename"
        assert meta["doc_type"] in VALID_TYPES, f"{path.name}: bad doc_type {meta['doc_type']}"
        assert meta["status"] in VALID_STATUS, f"{path.name}: bad status {meta['status']}"


def test_supersedes_references_resolve(finops_paths):
    ids = {path.stem for path in finops_paths}
    for path in finops_paths:
        target = front_matter(path.read_text(encoding="utf-8")).get("supersedes")
        if target:
            assert target in ids, f"{path.name} supersedes unknown doc '{target}'"


def test_every_month_has_a_statement(finops_docs):
    for month in MONTHS:
        assert f"meridian-ai-usage-{month}" in finops_docs


# ── the stale rate card trap ─────────────────────────────────────────────────


def test_rate_cards_disagree(finops_docs):
    """The recency trap only works if the two cards actually contradict."""
    old = finops_docs[RATE_CARD_2025_10.doc_id]
    new = finops_docs[RATE_CARD_2026_01.doc_id]

    assert front_matter(old)["status"] == "superseded"
    assert front_matter(new)["status"] == "current"
    assert front_matter(new)["supersedes"] == RATE_CARD_2025_10.doc_id

    changed = [
        model
        for model in MODEL_NAMES
        if RATE_CARD_2025_10.rates[model] != RATE_CARD_2026_01.rates[model]
    ]
    assert changed, "the two rate cards are identical — there is no trap"

    for model in changed:
        for rate in RATE_CARD_2025_10.rates[model]:
            if rate > 0:
                assert f"${rate:,.2f}".rstrip("0").rstrip(".") in old or str(rate) in old

    assert "$50.00" in old and "$40.00" in new, "gpt-5.5 output rate must differ on the page"


def test_superseded_rate_card_does_not_announce_its_own_obsolescence(finops_docs):
    """A stale document that warns you it is stale is not a trap, it is a hint.

    Real superseded documents carry no such warning — that is precisely what
    makes them dangerous in a retrieval corpus. Recency belongs in the `status`
    and `effective_date` metadata, where it can be governed, not in prose the
    model can simply read off the page.
    """
    old = _body(finops_docs[RATE_CARD_2025_10.doc_id]).lower()
    for tell in ("superseded", "no longer", "do not use", "out of date", "replaced by"):
        assert tell not in old, (
            f"The October 2025 rate card announces its own obsolescence ('{tell}'). "
            "That defeats the stale-rate-card trap."
        )

    new = _body(finops_docs[RATE_CARD_2026_01.doc_id]).lower()
    for tell in ("previously", "reduced from", "was $", "old rate"):
        assert tell not in new, (
            f"The January 2026 rate card carries the superseded rates ('{tell}'). "
            "That does the agent's job for it."
        )


def test_statements_price_against_the_card_in_effect(finops_docs):
    assert set(EXPECTED_RATE_CARD) == set(MONTHS)
    for month, expected in EXPECTED_RATE_CARD.items():
        text = finops_docs[f"meridian-ai-usage-{month}"]
        assert f"**Rate card applied:** `{expected}`" in text, (
            f"{month} statement does not name the card in effect for that period"
        )
        # The helper must agree with the literal above, in both directions.
        assert rate_card_for(month).doc_id == expected


# ── planted PII ──────────────────────────────────────────────────────────────


def test_exactly_one_document_declares_pii(finops_paths):
    flagged = [
        path.stem
        for path in finops_paths
        if front_matter(path.read_text(encoding="utf-8"))["contains_pii"]
    ]
    assert flagged == [PII_DOC], (
        f"Expected exactly one PII document, found {flagged}. "
        "Unflagged PII would escape the handling rules."
    )


def test_pii_document_explains_why_it_exists(finops_docs):
    text = finops_docs[PII_DOC]
    assert "Why this document exists" in text
    assert "does not exist" in text


@pytest.mark.parametrize(
    ("label", "pattern", "reserved"),
    [
        ("SSN", r"\b(\d{3})-(\d{2})-(\d{4})\b", lambda m: m.group(1) == "000"),
        (
            "phone",
            r"\(\d{3}\)\s*(\d{3})-(\d{4})\b",
            lambda m: m.group(1) == "555" and m.group(2).startswith("01"),
        ),
        (
            "email",
            r"\b[\w.+-]+@([\w.-]+\.\w+)\b",
            lambda m: m.group(1).endswith(("example.com", "example.org", "example.net")),
        ),
    ],
)
def test_identifiers_use_reserved_fiction_formats(finops_paths, label, pattern, reserved):
    for path in finops_paths:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(pattern, text):
            assert reserved(match), (
                f"{path.name} contains a {label} outside the reserved-for-fiction "
                f"range: {match.group(0)!r}. Synthetic data must be unmistakably synthetic."
            )


# ── arithmetic: monthly statements ───────────────────────────────────────────


@pytest.mark.parametrize("month", MONTHS)
def test_bu_detail_tables_add_up(finops_docs, month):
    """Each per-BU detail table's Total row must equal the sum of its model rows."""
    text = finops_docs[f"meridian-ai-usage-{month}"]

    for bu in BUSINESS_UNITS:
        rows = table_after(text, f"### {bu.code} — {bu.name}")
        body, total = rows[1:-1], rows[-1]
        assert body, f"{month} {bu.code}: no model rows"
        assert clean(total[0]) == "Total"

        for column in (1, 2, 3, 4):
            summed = sum(count(row[column]) for row in body)
            assert summed == count(total[column]), (
                f"{month} {bu.code}: column {column} does not add up "
                f"({summed} vs {count(total[column])})"
            )

        summed_cost = sum((money(row[5]) for row in body), Decimal(0))
        assert summed_cost == money(total[5]), f"{month} {bu.code}: metered cost does not add up"


def parse_rate_card(text: str) -> dict[str, tuple[Decimal, Decimal, Decimal]]:
    """Read the rates off the rate-card page.

    Deliberately NOT read from `finops_data.RATE_CARDS`. An earlier version of
    this test recomputed costs with `cost_for`, which calls the same
    `rate_card_for` the test was meant to validate — so when a tamper test
    pinned every month to the January card, the corpus regenerated at the wrong
    prices and the test agreed with the bug and passed. A pricing test that
    shares its pricing function with the code under test checks nothing.
    """
    rates: dict[str, tuple[Decimal, Decimal, Decimal]] = {}
    for row in table_after(text, "# Model Rate Card")[1:]:
        rate_out = Decimal(0) if clean(row[4]) == "n/a" else money(row[4])
        rates[clean(row[0])] = (money(row[2]), money(row[3]), rate_out)
    return rates


@pytest.mark.parametrize("month", MONTHS)
def test_detail_rows_reprice_from_the_stated_rate_card(finops_docs, month):
    """Recompute every line from its token counts and the rates on the card the
    statement names. Catches a period priced against the wrong card."""
    text = finops_docs[f"meridian-ai-usage-{month}"]

    named = re.search(r"\*\*Rate card applied:\*\* `([\w-]+)`", text)
    assert named, f"{month} statement does not name a rate card"
    assert named.group(1) == EXPECTED_RATE_CARD[month], (
        f"{month} is priced against {named.group(1)}, but the card in effect for "
        f"that period is {EXPECTED_RATE_CARD[month]}. Consumption is never "
        "repriced against a later card."
    )
    rates = parse_rate_card(finops_docs[named.group(1)])

    for bu in BUSINESS_UNITS:
        rows = table_after(text, f"### {bu.code} — {bu.name}")
        for row in rows[1:-1]:
            model = clean(row[0])
            rate_in, rate_cached, rate_out = rates[model]
            recomputed = (
                (count(row[2]) * rate_in + count(row[3]) * rate_cached + count(row[4]) * rate_out)
                / Decimal(1_000_000)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assert recomputed == money(row[5]), (
                f"{month} {bu.code} {model}: page says {money(row[5])}, "
                f"the {named.group(1)} card says {recomputed}"
            )


@pytest.mark.parametrize("month", MONTHS)
def test_month_summary_matches_detail_and_applies_the_uplift(finops_docs, month):
    text = finops_docs[f"meridian-ai-usage-{month}"]
    summary = table_after(text, "## Summary by business unit")
    body, total = summary[1:-1], summary[-1]

    assert [clean(row[0]) for row in body] == BU_CODES

    for row in body:
        code = clean(row[0])
        bu = next(b for b in BUSINESS_UNITS if b.code == code)
        detail = table_after(text, f"### {bu.code} — {bu.name}")[-1]

        assert count(row[3]) == count(detail[1]), f"{month} {code}: request count disagrees"
        assert money(row[5]) == money(detail[5]), f"{month} {code}: metered cost disagrees"

        tokens = count(detail[2]) + count(detail[3]) + count(detail[4])
        assert count(row[4]) == tokens, f"{month} {code}: token total disagrees"

        expected_billed = (money(row[5]) * (Decimal(1) + PLATFORM_UPLIFT)).quantize(Decimal("0.01"))
        assert money(row[6]) == expected_billed, f"{month} {code}: uplift misapplied"

    for column in (3, 4):
        assert sum(count(row[column]) for row in body) == count(total[column])
    for column in (5, 6):
        assert sum((money(row[column]) for row in body), Decimal(0)) == money(total[column])


@pytest.mark.parametrize("month", MONTHS)
def test_month_model_summary_ties_to_the_platform_total(finops_docs, month):
    text = finops_docs[f"meridian-ai-usage-{month}"]
    by_model = table_after(text, "## Summary by model")[1:]
    by_bu_total = table_after(text, "## Summary by business unit")[-1]

    assert sum(count(row[1]) for row in by_model) == count(by_bu_total[3])
    assert sum(count(row[2]) for row in by_model) == count(by_bu_total[4])
    assert sum((money(row[3]) for row in by_model), Decimal(0)) == money(by_bu_total[5])


# ── arithmetic: half-year summary ────────────────────────────────────────────


def test_summary_matrix_ties_to_every_monthly_statement(finops_docs):
    """The load-bearing cross-document check.

    If the summary and the statements disagree, then any answer sourced from
    either is unverifiable, and an evaluation built on this corpus grades
    nothing.
    """
    matrix = summary_matrix(finops_docs)
    header, body, total = matrix[0], matrix[1:-1], matrix[-1]

    assert [clean(cell) for cell in header[1 : len(MONTHS) + 1]] == [
        f"{name.split()[0][:3]} {month[:4]}"
        for name, month in ((_month_name(m), m) for m in MONTHS)
    ]

    for row in body:
        code = clean(row[0])
        for index, month in enumerate(MONTHS, start=1):
            statement = finops_docs[f"meridian-ai-usage-{month}"]
            stated = next(
                money(line[6])
                for line in table_after(statement, "## Summary by business unit")[1:-1]
                if clean(line[0]) == code
            )
            assert money(row[index]) == stated, (
                f"summary cell ({code}, {month}) is {money(row[index])} but the "
                f"{month} statement bills {stated}"
            )

        row_total = sum((money(row[i]) for i in range(1, len(MONTHS) + 1)), Decimal(0))
        assert money(row[-1]) == row_total, f"summary H1 total for {code} does not add up"

    for index in range(1, len(MONTHS) + 2):
        column_total = sum((money(row[index]) for row in body), Decimal(0))
        assert money(total[index]) == column_total, f"summary column {index} does not add up"


def _month_name(month: str) -> str:
    from finops_data import MONTH_NAMES

    return MONTH_NAMES[month]


def test_summary_model_table_ties_to_the_monthly_statements(finops_docs):
    rows = table_after(finops_docs[SUMMARY_DOC], "## Metered cost by model")
    body, total = rows[1:-1], rows[-1]

    assert [clean(row[0]) for row in body] == list(MODEL_NAMES)

    for row in body:
        model = clean(row[0])
        expected = Decimal(0)
        requests = 0
        tokens = 0
        for month in MONTHS:
            statement = finops_docs[f"meridian-ai-usage-{month}"]
            for line in table_after(statement, "## Summary by model")[1:]:
                if clean(line[0]) == model:
                    requests += count(line[1])
                    tokens += count(line[2])
                    expected += money(line[3])
        assert count(row[1]) == requests, f"{model}: H1 request count does not tie"
        assert count(row[2]) == tokens, f"{model}: H1 token count does not tie"
        assert money(row[3]) == expected, f"{model}: H1 metered cost does not tie"

    assert sum(count(row[1]) for row in body) == count(total[1])
    assert sum(count(row[2]) for row in body) == count(total[2])
    assert sum((money(row[3]) for row in body), Decimal(0)) == money(total[3])


def test_summary_budget_variance_uses_the_policy_budgets(finops_docs):
    policy = table_after(finops_docs["meridian-ai-budget-quota-policy"], "## 1. Budget allocation")
    budgets = {clean(row[0]): money(row[3]) for row in policy[1:-1]}
    assert set(budgets) == set(BU_CODES)

    variance = table_after(finops_docs[SUMMARY_DOC], "## Budget variance")[1:]
    matrix = summary_matrix_by_bu(finops_docs)

    for row in variance:
        code = clean(row[0])
        assert money(row[1]) == budgets[code] * len(MONTHS), f"{code}: H1 budget disagrees"
        assert money(row[2]) == money(matrix[code][-1]), f"{code}: H1 billed disagrees"
        assert money(row[3]) == money(row[2]) - money(row[1]), f"{code}: variance does not add up"


def test_declared_breaches_are_exactly_the_real_breaches(finops_docs):
    """A breach table that under-reports is worse than no breach table."""
    policy = table_after(finops_docs["meridian-ai-budget-quota-policy"], "## 1. Budget allocation")
    budgets = {clean(row[0]): money(row[3]) for row in policy[1:-1]}

    matrix = summary_matrix(finops_docs)
    expected = set()
    for row in matrix[1:-1]:
        code = clean(row[0])
        for index, month in enumerate(MONTHS, start=1):
            if money(row[index]) > budgets[code]:
                expected.add((month, code))

    declared = set()
    for row in table_after(finops_docs[SUMMARY_DOC], "## Monthly budget breaches")[1:]:
        name = clean(row[0])
        month = next(m for m in MONTHS if _month_name(m) == name)
        declared.add((month, clean(row[1])))

    assert declared == expected, (
        f"Declared breaches {sorted(declared)} do not match the matrix "
        f"{sorted(expected)}. A cost report that hides an overage is the failure "
        "mode this demo exists to catch."
    )


# ── staged events ────────────────────────────────────────────────────────────


def test_the_anomaly_is_large_enough_to_be_unmissable(finops_docs):
    row = summary_matrix_by_bu(finops_docs)[ANOMALY_BU]
    spike_index = MONTHS.index(ANOMALY_MONTH) + 1
    spike = money(row[spike_index])
    baseline = money(row[spike_index - 1])

    assert spike > baseline * 4, (
        f"The {ANOMALY_MONTH} anomaly for {ANOMALY_BU} is only "
        f"{spike / baseline:.1f}x baseline. An anomaly an agent could plausibly "
        "miss does not test anything."
    )


def test_the_anomaly_review_agrees_with_the_statement(finops_docs):
    review = finops_docs["meridian-ai-cost-anomaly-2026-02"]
    statement = finops_docs[f"meridian-ai-usage-{ANOMALY_MONTH}"]

    stated = next(
        money(row[5])
        for row in table_after(statement, "## Summary by business unit")[1:-1]
        if clean(row[0]) == ANOMALY_BU
    )
    assert f"${stated:,.2f}" in review, (
        "The incident review quotes a February metered cost that the February "
        "statement does not support."
    )

    detail = table_after(review, "## Consumption detail")[1:]
    assert len(detail) == 2, "the review must show the affected period against its baseline"


def test_forecast_is_labelled_as_a_projection(finops_docs):
    text = finops_docs["meridian-ai-cost-forecast-fy26h2"]
    assert front_matter(text)["doc_type"] == "forecast"
    assert "not statements of" in text, (
        "The forecast must state that its figures carry no billing effect — that "
        "is what makes quoting them as actuals a gradeable error rather than an "
        "ambiguity in the corpus."
    )


# ── the committed corpus matches the generator ───────────────────────────────


def test_committed_corpus_is_current():
    """`--check` in a test, so a stale corpus fails the gate and not the demo."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "scripts" / "generate_finops_corpus.py"), "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        "The committed corpus is out of date with scripts/finops_data.py.\n"
        f"{result.stdout}\n{result.stderr}\n"
        "Run: python scripts/generate_finops_corpus.py"
    )


def test_generation_is_deterministic(tmp_path: Path):
    """Regenerating must produce byte-identical documents.

    Volumes are derived from a hash of (business unit, month) rather than a
    seeded PRNG precisely so this holds across interpreters. If it ever fails,
    the corpus cannot be diffed in a PR and no dataset scored against it means
    anything.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_finops_corpus import build_documents

    first = build_documents()
    second = build_documents()
    assert first == second

    committed = {
        path.stem: path.read_text(encoding="utf-8") for path in FINOPS_CORPUS_DIR.glob("*.md")
    }
    assert committed == first
