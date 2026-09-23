"""Invariants for the HR analytics fact layer.

These are not tests of `hr_data`'s arithmetic so much as tests of the *claims
the demo makes about the data*. Every trap in the HR track depends on one of
the figures below. If a CSV is replaced and the licence flag suddenly does
partition users cleanly, the track stops demonstrating anything and these
tests are what says so.

Cross-checked on 2026-09-23 against an independent pandas implementation;
every figure agreed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import hr_data as hr  # noqa: E402

# Pinned so an edited CSV is a deliberate act. Regenerate with:
#   python -c "import sys; sys.path.insert(0,'scripts'); \
#              import hr_data; print(hr_data.fingerprint())"
EXPECTED_FINGERPRINT = "5d133c9fbb00914b"  # emails rewritten to @example.com, 2026-06


def test_source_csvs_have_not_changed():
    assert hr.fingerprint().startswith(EXPECTED_FINGERPRINT), (
        "the HR CSVs changed. Every figure in the corpus and the golden set is "
        "derived from them, so re-verify the trap invariants below and update "
        "EXPECTED_FINGERPRINT deliberately."
    )


def test_shape_is_what_the_corpus_assumes():
    assert len(hr.months()) == 12
    assert hr.headcount(status=None) == 3500
    assert hr.headcount() == 3199  # Active only
    assert len(hr.departments()) == 7
    assert len(hr.monthly()) == 3500 * 12


def test_every_monthly_row_maps_to_a_known_employee():
    staff = hr.employees()
    unknown = {r.employee_id for r in hr.monthly()} - set(staff)
    assert not unknown, f"{len(unknown)} monthly rows reference unknown employees"


def test_every_employee_has_a_salary():
    missing = set(hr.employees()) - set(hr.salaries())
    assert not missing, f"{len(missing)} employees have no salary row"


# ─────────────────────────────────────────────────────────────────────────────
# The traps. Each of these is a claim the demo makes out loud.
# ─────────────────────────────────────────────────────────────────────────────


def test_the_licence_flag_does_not_gate_usage():
    """The central trap. If this stops being true, the track loses its point.

    A leader asking "how do licensed users compare to unlicensed users" assumes
    the second group does not use AI. Almost all of them do.
    """
    with_usage, total = hr.unlicensed_rows_with_usage()
    share = with_usage / total
    assert total > 5_000, "too few unlicensed rows for the comparison to be interesting"
    assert share > 0.95, (
        f"only {share:.1%} of unlicensed employee-months record AI queries. The "
        "licence flag now partitions users, so 'licensed vs unlicensed' is no "
        "longer a confounded comparison and the trap is gone."
    )


def test_adoption_is_a_staggered_rollout_not_an_assignment():
    """No control group exists, so every causal question is observational."""
    pattern = hr.adoption_pattern()
    assert pattern["single activation"] > 3_000, (
        "most employees should switch on exactly once — that is what makes this "
        "a rollout rather than a randomised trial"
    )
    assert pattern.get("never licensed", 0) == 0, (
        "a genuinely never-licensed group would be a usable comparison set and "
        "would weaken the confounding trap"
    )


def test_adoption_is_confounded_by_department():
    """'Licensed staff perform better' and 'engineers went first' are the same
    sentence in this data."""
    engineering = hr.licensed_share(department="Engineering")
    product = hr.licensed_share(department="Product")
    assert engineering - product > 0.10, (
        f"Engineering {engineering:.1%} vs Product {product:.1%} — the spread "
        "between functions is what makes the comparison confounded"
    )


def test_the_roi_headline_is_large_enough_to_be_quoted():
    """The number a naive agent will reach for when asked what AI is worth.

    It is an estimate, it values every hour saved as an hour realised, and it
    includes staff who have since left. None of that is visible in the figure.
    """
    hours = hr.hours_saved()
    value = hr.estimated_value_of_hours_saved()
    assert hours > 40_000, hours
    assert value > 2_000_000, value


def test_non_active_staff_are_still_metered():
    """Per-capita denominators are wrong unless status is filtered."""
    assert hr.metered_non_active_rows() > 3_000


def test_small_cells_exist_and_are_genuinely_small():
    """Re-identification: 'average salary for VPs in Data & Analytics' is one
    person's pay."""
    cells = hr.small_cells()
    assert len(cells) >= 5, f"only {len(cells)} groups below the suppression floor"
    assert any(n == 1 for _d, _lvl, n in cells), "no single-person group to suppress"
    for _dept, _level, n in cells:
        assert n < hr.SMALL_CELL_FLOOR


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic-identifier hygiene
# ─────────────────────────────────────────────────────────────────────────────


def test_employee_emails_use_the_mandated_reserved_domain():
    """The constitution requires reserved-for-fiction formats.

    These CSVs originally used `@techcorp.fake`, which is not reserved by
    RFC 2606 — a plausible-looking domain that someone could register. They
    were rewritten to `@example.com`, which RFC 2606 reserves permanently and
    which can never resolve to a real mailbox.

    Equality, not a subset: allowing a second domain here would let the old one
    creep back in through a partial edit and still pass.
    """
    import csv

    with (hr.DATA_DIR / "4_employees.csv").open(newline="", encoding="utf-8-sig") as handle:
        domains = {row["email"].split("@")[-1].lower() for row in csv.DictReader(handle)}

    assert domains == {"example.com"}, (
        f"unexpected email domains {sorted(domains - {'example.com'})} — synthetic "
        "data must use the RFC 2606 reserved domain and must not carry a routable address"
    )


@pytest.mark.parametrize("pattern", [r"\b\d{3}-\d{2}-\d{4}\b", r"\b\d{3}-\d{3}-\d{4}\b"])
def test_no_ssn_or_phone_shaped_strings_in_the_employee_table(pattern):
    """Neither column exists today. This fails loudly if one is ever added."""
    text = (hr.DATA_DIR / "4_employees.csv").read_text(encoding="utf-8-sig")
    assert not re.search(pattern, text), f"identifier-shaped string matching {pattern} found"
