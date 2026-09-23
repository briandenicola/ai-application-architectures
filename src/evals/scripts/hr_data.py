"""Fact layer for the HR analytics track.

Unlike `finops_data`, nothing here is synthesised. The CSVs in
`datasets/hr_analytics/` are the source of truth, and this module is the only
thing that reads them. The corpus renderer, the golden-set builder and the
tests all query through here, so a figure printed in a report and the same
figure in an expected answer cannot disagree — they are the same call.

Stdlib only, deliberately. pandas would make this shorter and would also put a
150MB wheel in the azd provisioning hook for the sake of some group-bys over
42,000 rows.

## What makes this track different

The FinOps corpus fails an agent on arithmetic. This one fails it on
inference. Every headline figure below is *correct*; the trap is what a reader
concludes from it:

- 99.5% of unlicensed employee-months still record AI queries, so the licence
  flag does not partition users into "uses AI" and "does not".
- Adoption was a staggered rollout skewed to Engineering, so any comparison
  between licensed and unlicensed staff is confounded by function.
- `ai_hours_saved_est` is an estimate. It sums to a large, quotable number.

See `docs/hr-traps.md`.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "datasets" / "hr_analytics"

FILES = (
    "1_locations.csv",
    "2_departments.csv",
    "3_job_titles.csv",
    "4_employees.csv",
    "6_monthly_employee_metrics.csv",
    "7_salaries.csv",
    "8_performance_reviews.csv",
)

# 5_daily_activity.csv is deliberately not loaded. It is 1.28M rows and nothing
# in the corpus needs daily grain; the monthly table already carries the hours.

# Suppression floor for any cell reported by group. Five is the conventional
# threshold in workforce reporting, and this dataset has seven groups below it.
SMALL_CELL_FLOOR = 5

CENT = Decimal("0.01")
WORK_HOURS_PER_YEAR = Decimal(2080)


def _read(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _norm_month(raw: str) -> str:
    """'1/1/2025' -> '2025-01'.

    The CSVs are not internally consistent about dates: the monthly table and
    the employee table use M/D/YYYY while daily activity uses ISO. Normalising
    on read means the inconsistency cannot reach a rendered document.
    """
    month, _day, year = raw.split("/")
    return f"{int(year):04d}-{int(month):02d}"


@dataclass(frozen=True)
class Employee:
    employee_id: int
    department: str
    cost_center: str
    title: str
    level: str
    location: str
    status: str
    is_remote: bool
    hire_date: str


@dataclass(frozen=True)
class MonthRow:
    employee_id: int
    month: str
    active_hours: Decimal
    expected_hours: Decimal
    licensed: bool
    queries: int
    hours_saved_est: Decimal


@lru_cache(maxsize=1)
def employees() -> dict[int, Employee]:
    departments = {r["department_id"]: r for r in _read("2_departments.csv")}
    titles = {r["job_id"]: r for r in _read("3_job_titles.csv")}
    locations = {r["location_id"]: r for r in _read("1_locations.csv")}

    out: dict[int, Employee] = {}
    for row in _read("4_employees.csv"):
        dept = departments[row["department_id"]]
        title = titles[row["job_id"]]
        loc = locations[row["location_id"]]
        out[int(row["employee_id"])] = Employee(
            employee_id=int(row["employee_id"]),
            department=dept["department_name"],
            cost_center=dept["cost_center"],
            title=title["title"],
            level=title["level"],
            location=loc["city"],
            status=row["status"],
            is_remote=row["is_remote"].strip().upper() == "TRUE",
            hire_date=row["hire_date"],
        )
    return out


@lru_cache(maxsize=1)
def monthly() -> tuple[MonthRow, ...]:
    rows = []
    for row in _read("6_monthly_employee_metrics.csv"):
        rows.append(
            MonthRow(
                employee_id=int(row["employee_id"]),
                month=_norm_month(row["month"]),
                active_hours=Decimal(row["total_monthly_active_hours"]),
                expected_hours=Decimal(row["expected_monthly_hours"]),
                licensed=row["ai_license_active"] == "1",
                queries=int(row["ai_queries_made"]),
                hours_saved_est=Decimal(row["ai_hours_saved_est"]),
            )
        )
    return tuple(rows)


@lru_cache(maxsize=1)
def salaries() -> dict[int, Decimal]:
    rows = _read("7_salaries.csv")
    return {int(r["employee_id"]): Decimal(r["annual_base_salary"]) for r in rows}


@lru_cache(maxsize=1)
def months() -> tuple[str, ...]:
    return tuple(sorted({r.month for r in monthly()}))


@lru_cache(maxsize=1)
def departments() -> tuple[str, ...]:
    return tuple(sorted({e.department for e in employees().values()}))


def rows(
    *,
    month: str | None = None,
    department: str | None = None,
    licensed: bool | None = None,
    status: str | None = None,
) -> list[MonthRow]:
    """Filtered employee-months. The one place slicing happens."""
    staff = employees()
    out = []
    for row in monthly():
        if month is not None and row.month != month:
            continue
        if licensed is not None and row.licensed != licensed:
            continue
        person = staff[row.employee_id]
        if department is not None and person.department != department:
            continue
        if status is not None and person.status != status:
            continue
        out.append(row)
    return out


def headcount(*, department: str | None = None, status: str | None = "Active") -> int:
    return sum(
        1
        for e in employees().values()
        if (department is None or e.department == department)
        and (status is None or e.status == status)
    )


def licensed_share(*, month: str | None = None, department: str | None = None) -> Decimal:
    """Share of employee-months carrying an active licence."""
    subset = rows(month=month, department=department)
    if not subset:
        return Decimal(0)
    n = sum(1 for r in subset if r.licensed)
    return (Decimal(n) / Decimal(len(subset))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def queries(*, month: str | None = None, department: str | None = None, licensed=None) -> int:
    return sum(r.queries for r in rows(month=month, department=department, licensed=licensed))


def hours_saved(*, month: str | None = None, department: str | None = None, licensed=None):
    total = sum(
        (r.hours_saved_est for r in rows(month=month, department=department, licensed=licensed)),
        Decimal(0),
    )
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def unlicensed_rows_with_usage() -> tuple[int, int]:
    """(rows with queries, total unlicensed rows).

    The single most important pair of numbers in this dataset. If the second
    number is large and the first is nearly as large, the licence flag does not
    mean what a reader assumes it means.
    """
    unlicensed = rows(licensed=False)
    return sum(1 for r in unlicensed if r.queries > 0), len(unlicensed)


def adoption_pattern() -> dict[str, int]:
    """How the licence flag behaves per employee over the twelve months."""
    by_emp: dict[int, list[tuple[str, bool]]] = defaultdict(list)
    for row in monthly():
        by_emp[row.employee_id].append((row.month, row.licensed))

    counts: dict[str, int] = defaultdict(int)
    for series in by_emp.values():
        flags = [licensed for _month, licensed in sorted(series)]
        if all(flags):
            counts["always licensed"] += 1
        elif not any(flags):
            counts["never licensed"] += 1
        elif sum(1 for a, b in zip(flags, flags[1:], strict=False) if a != b) == 1:
            counts["single activation"] += 1
        else:
            counts["intermittent"] += 1
    return dict(counts)


def estimated_value_of_hours_saved() -> Decimal:
    """Hours saved priced at each employee's own base rate.

    Deliberately provided, because this is the number a naive agent will
    produce when asked what the AI programme is worth — and it is built on an
    estimate, values every hour saved as an hour realised, and counts staff who
    have since left. It belongs in the fact layer so the golden set can assert
    exactly which figure was quoted.
    """
    pay = salaries()
    total = Decimal(0)
    for row in monthly():
        rate = pay[row.employee_id] / WORK_HOURS_PER_YEAR
        total += row.hours_saved_est * rate
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def small_cells() -> list[tuple[str, str, int]]:
    """(department, level, n) for every group below the suppression floor."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for person in employees().values():
        if person.status == "Active":
            counts[(person.department, person.level)] += 1
    return sorted((d, lvl, n) for (d, lvl), n in counts.items() if n < SMALL_CELL_FLOOR)


def metered_non_active_rows() -> int:
    """Employee-months recorded against staff who are not active."""
    return len(rows(status="Terminated")) + len(rows(status="Leave"))


# ── accessors the corpus renderer needs ──────────────────────────────────────

LEVEL_ORDER = ("C-Suite", "VP", "Director", "Manager", "IC-Senior", "IC-Mid", "IC-Entry")


@lru_cache(maxsize=1)
def levels() -> tuple[str, ...]:
    """Seniority levels, ranked rather than alphabetical.

    Any level absent from LEVEL_ORDER is appended rather than dropped — a
    silently missing level would understate a headcount table.
    """
    present = {e.level for e in employees().values()}
    ranked = [lvl for lvl in LEVEL_ORDER if lvl in present]
    return tuple(ranked + sorted(present - set(ranked)))


@lru_cache(maxsize=1)
def locations() -> tuple[str, ...]:
    return tuple(sorted({e.location for e in employees().values()}))


def staff(
    *,
    department: str | None = None,
    level: str | None = None,
    location: str | None = None,
    status: str | None = "Active",
) -> list[Employee]:
    return [
        e
        for e in employees().values()
        if (department is None or e.department == department)
        and (level is None or e.level == level)
        and (location is None or e.location == location)
        and (status is None or e.status == status)
    ]


def headcount_grid() -> dict[tuple[str, str], int]:
    """Active headcount by (department, level). Includes the small cells."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for person in staff():
        counts[(person.department, person.level)] += 1
    return dict(counts)


def remote_share(*, department: str | None = None) -> Decimal:
    people = staff(department=department)
    if not people:
        return Decimal(0)
    remote = sum(1 for p in people if p.is_remote)
    return (Decimal(remote) / Decimal(len(people))).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def mean_salary(*, department: str | None = None, level: str | None = None) -> tuple[int, Decimal]:
    """(n, mean base salary) for a group.

    Returns the count alongside the figure deliberately. A mean without its n
    cannot be suppression-checked by the caller, and this dataset has groups
    of one.
    """
    pay = salaries()
    people = staff(department=department, level=level)
    if not people:
        return 0, Decimal(0)
    total = sum((pay[p.employee_id] for p in people), Decimal(0))
    return len(people), (total / Decimal(len(people))).quantize(CENT, rounding=ROUND_HALF_UP)


def active_hours(*, month: str | None = None, department: str | None = None) -> Decimal:
    subset = rows(month=month, department=department)
    return sum((r.active_hours for r in subset), Decimal(0)).quantize(CENT, rounding=ROUND_HALF_UP)


def mean_active_hours(*, month: str | None = None, department: str | None = None) -> Decimal:
    subset = rows(month=month, department=department)
    if not subset:
        return Decimal(0)
    total = sum((r.active_hours for r in subset), Decimal(0))
    return (total / Decimal(len(subset))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def licensed_employee_ids(month: str) -> set[int]:
    return {r.employee_id for r in rows(month=month) if r.licensed}


def first_licensed_month(employee_id: int) -> str | None:
    """When an employee's licence first appears. Drives the rollout timeline."""
    got = sorted(r.month for r in monthly() if r.employee_id == employee_id and r.licensed)
    return got[0] if got else None


@lru_cache(maxsize=1)
def rollout_timeline() -> dict[str, int]:
    """Employees whose licence first appears in each month.

    This is the evidence that adoption was a staggered rollout. A reader who
    sees it cannot honestly describe the unlicensed group as a control.
    """
    first: dict[int, str] = {}
    for row in monthly():
        if not row.licensed:
            continue
        current = first.get(row.employee_id)
        if current is None or row.month < current:
            first[row.employee_id] = row.month
    counts: dict[str, int] = defaultdict(int)
    for month in first.values():
        counts[month] += 1
    return {month: counts.get(month, 0) for month in months()}


@lru_cache(maxsize=1)
def performance() -> dict[int, list[tuple[str, Decimal, str]]]:
    """(review_date, score, potential) per employee. Restricted data.

    Scores are decimal (2.9, 4.1), not integer. Reading them as int raises
    rather than truncating, which is the behaviour we want — a silently
    truncated performance score would be a fabricated one.
    """
    out: dict[int, list[tuple[str, Decimal, str]]] = defaultdict(list)
    for row in _read("8_performance_reviews.csv"):
        out[int(row["employee_id"])].append(
            (row["review_date"], Decimal(row["performance_score"]), row["potential_rating"])
        )
    return dict(out)


def mean_performance(*, department: str | None = None) -> tuple[int, Decimal]:
    reviews = performance()
    people = staff(department=department)
    scores = [score for p in people for _d, score, _pot in reviews.get(p.employee_id, [])]
    if not scores:
        return 0, Decimal(0)
    total = sum(scores, Decimal(0))
    return len(scores), (total / Decimal(len(scores))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def adoption_vs_performance() -> list[tuple[str, Decimal, Decimal, int]]:
    """(department, licensed share, mean performance, active headcount).

    The table that makes the confound visible. Ordered by licensed share so
    the correlation with function is impossible to miss — and so is the fact
    that it is a correlation.
    """
    out = []
    for dept in departments():
        share = licensed_share(department=dept)
        _n, score = mean_performance(department=dept)
        out.append((dept, share, score, headcount(department=dept)))
    return sorted(out, key=lambda r: r[1], reverse=True)


@lru_cache(maxsize=1)
def fingerprint() -> str:
    """SHA-256 over every source CSV.

    A rendered corpus is only reproducible if its inputs are. If someone edits
    a CSV, this changes, and the test that pins it fails rather than the
    documents silently describing different data.
    """
    digest = hashlib.sha256()
    for name in FILES:
        digest.update(name.encode("utf-8"))
        digest.update((DATA_DIR / name).read_bytes())
    return digest.hexdigest()
