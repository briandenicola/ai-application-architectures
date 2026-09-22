"""Deterministic synthetic data model for the AI Platform FinOps corpus.

Separated from the renderer so the numbers have exactly one origin. The corpus
markdown, the golden dataset and the tests all read from here, which is what
makes "the agent got the arithmetic wrong" a defensible claim rather than an
argument about which document was right.

Nothing here is random at run time. Volumes are derived from a SHA-256 of the
(business unit, month) pair, so regenerating the corpus on any machine, on any
Python, produces byte-identical documents. A corpus that drifts between
regenerations cannot be diffed in a PR, and a dataset scored against a drifting
corpus is scored against nothing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
MILLION = Decimal(1_000_000)

# Fiscal H1 FY26. Six months, deliberately straddling a rate-card change so that
# "what did X cost in December" and "what does X cost now" have different answers.
MONTHS: tuple[str, ...] = (
    "2025-10",
    "2025-11",
    "2025-12",
    "2026-01",
    "2026-02",
    "2026-03",
)

MONTH_NAMES: dict[str, str] = {
    "2025-10": "October 2025",
    "2025-11": "November 2025",
    "2025-12": "December 2025",
    "2026-01": "January 2026",
    "2026-02": "February 2026",
    "2026-03": "March 2026",
}

MONTH_END: dict[str, str] = {
    "2025-10": "2025-10-31",
    "2025-11": "2025-11-30",
    "2025-12": "2025-12-31",
    "2026-01": "2026-01-31",
    "2026-02": "2026-02-28",
    "2026-03": "2026-03-31",
}

# Platform uplift applied to metered consumption when it is charged to a cost
# centre. The gap between "what the meter says" and "what the BU is billed" is
# the single most common source of a confidently wrong answer in real FinOps
# conversations, so the corpus keeps both numbers and never conflates them.
PLATFORM_UPLIFT = Decimal("0.08")


@dataclass(frozen=True)
class Model:
    name: str
    kind: str  # "chat" | "embedding"
    purpose: str


MODELS: tuple[Model, ...] = (
    Model("gpt-5.5", "chat", "Reasoning tier. Agent planning, multi-step analysis."),
    Model("gpt-5.4-mini", "chat", "Volume tier. Classification, extraction, summarisation."),
    Model("gpt-4.1", "chat", "Legacy tier. Pre-migration workloads only."),
    Model("text-embedding-3-large", "embedding", "Retrieval over the governed document estate."),
    Model("text-embedding-3-small", "embedding", "High-volume similarity and dedup."),
)

MODEL_NAMES: tuple[str, ...] = tuple(m.name for m in MODELS)


@dataclass(frozen=True)
class RateCard:
    doc_id: str
    effective_date: str
    status: str
    supersedes: str | None
    # model -> (input, cached input, output) USD per 1,000,000 tokens
    rates: dict[str, tuple[Decimal, Decimal, Decimal]]


def _d(value: str) -> Decimal:
    return Decimal(value)


RATE_CARD_2025_10 = RateCard(
    doc_id="meridian-model-rate-card-2025-10",
    effective_date="2025-10-01",
    status="superseded",
    supersedes=None,
    rates={
        "gpt-5.5": (_d("12.50"), _d("1.25"), _d("50.00")),
        "gpt-5.4-mini": (_d("0.75"), _d("0.075"), _d("3.00")),
        "gpt-4.1": (_d("2.00"), _d("0.50"), _d("8.00")),
        "text-embedding-3-large": (_d("0.13"), _d("0.13"), _d("0")),
        "text-embedding-3-small": (_d("0.02"), _d("0.02"), _d("0")),
    },
)

RATE_CARD_2026_01 = RateCard(
    doc_id="meridian-model-rate-card-2026-01",
    effective_date="2026-01-01",
    status="current",
    supersedes="meridian-model-rate-card-2025-10",
    rates={
        "gpt-5.5": (_d("10.00"), _d("1.00"), _d("40.00")),
        "gpt-5.4-mini": (_d("0.60"), _d("0.06"), _d("2.40")),
        "gpt-4.1": (_d("2.00"), _d("0.50"), _d("8.00")),
        "text-embedding-3-large": (_d("0.13"), _d("0.13"), _d("0")),
        "text-embedding-3-small": (_d("0.02"), _d("0.02"), _d("0")),
    },
)

RATE_CARDS: tuple[RateCard, ...] = (RATE_CARD_2025_10, RATE_CARD_2026_01)


def rate_card_for(month: str) -> RateCard:
    """The card in effect on the date of consumption. Not the current card."""
    return RATE_CARD_2025_10 if month < "2026-01" else RATE_CARD_2026_01


@dataclass(frozen=True)
class Workload:
    model: str
    # Calls per unit of BU monthly volume. Chat multipliers sum to 1.0 by
    # convention; embedding multipliers are additional calls per agent turn.
    calls_per_unit: float
    avg_input_tokens: int
    avg_output_tokens: int
    cache_hit_rate: float


@dataclass(frozen=True)
class BusinessUnit:
    code: str
    name: str
    cost_center: str
    owner: str
    owner_email: str
    owner_phone: str
    monthly_budget: Decimal
    baseline_units: int
    monthly_growth: float
    workloads: tuple[Workload, ...]
    description: str


BUSINESS_UNITS: tuple[BusinessUnit, ...] = (
    BusinessUnit(
        code="WAS",
        name="Wealth Advisory Support",
        cost_center="CC-4101",
        owner="Dana Okafor",
        owner_email="dana.okafor@example.com",
        owner_phone="(212) 555-0142",
        monthly_budget=Decimal("9500"),
        baseline_units=196_000,
        monthly_growth=0.06,
        workloads=(
            Workload("gpt-5.5", 0.42, 5_600, 900, 0.38),
            Workload("gpt-5.4-mini", 0.58, 2_400, 420, 0.22),
            Workload("text-embedding-3-large", 0.90, 1_100, 0, 0.0),
        ),
        description="Advisor copilot answering firm-document questions in client meetings.",
    ),
    BusinessUnit(
        code="COK",
        name="Client Onboarding & KYC",
        cost_center="CC-4210",
        owner="Priya Raman",
        owner_email="priya.raman@example.com",
        owner_phone="(212) 555-0118",
        monthly_budget=Decimal("4400"),
        baseline_units=143_000,
        monthly_growth=0.04,
        workloads=(
            Workload("gpt-5.5", 0.18, 7_200, 1_150, 0.31),
            Workload("gpt-5.4-mini", 0.82, 3_100, 520, 0.44),
            Workload("text-embedding-3-small", 1.60, 780, 0, 0.0),
        ),
        description="Document extraction and identity verification triage.",
    ),
    BusinessUnit(
        code="CSV",
        name="Compliance Surveillance",
        cost_center="CC-4315",
        owner="Marcus Vidal",
        owner_email="marcus.vidal@example.com",
        owner_phone="(212) 555-0177",
        monthly_budget=Decimal("14000"),
        baseline_units=168_000,
        monthly_growth=0.05,
        workloads=(
            Workload("gpt-5.5", 0.55, 6_400, 1_050, 0.19),
            Workload("gpt-5.4-mini", 0.45, 2_900, 380, 0.27),
            Workload("text-embedding-3-large", 1.20, 1_400, 0, 0.0),
        ),
        description="Communications surveillance and escalation drafting.",
    ),
    BusinessUnit(
        code="INR",
        name="Investment Research",
        cost_center="CC-4402",
        owner="Lena Farrow",
        owner_email="lena.farrow@example.com",
        owner_phone="(212) 555-0163",
        monthly_budget=Decimal("16000"),
        baseline_units=121_000,
        monthly_growth=0.08,
        workloads=(
            Workload("gpt-5.5", 0.61, 9_800, 1_600, 0.24),
            Workload("gpt-5.4-mini", 0.39, 4_200, 610, 0.18),
            Workload("text-embedding-3-large", 1.05, 2_100, 0, 0.0),
        ),
        description="Filing and transcript synthesis for the research desk.",
    ),
    BusinessUnit(
        code="CCO",
        name="Contact Center Operations",
        cost_center="CC-4508",
        owner="Theo Brandt",
        owner_email="theo.brandt@example.com",
        owner_phone="(212) 555-0109",
        monthly_budget=Decimal("2900"),
        baseline_units=412_000,
        monthly_growth=0.03,
        workloads=(
            Workload("gpt-5.4-mini", 0.94, 1_900, 260, 0.61),
            Workload("gpt-5.5", 0.06, 4_100, 700, 0.29),
            Workload("text-embedding-3-small", 1.10, 620, 0, 0.0),
        ),
        description="Call summarisation, intent routing, and disposition coding.",
    ),
    BusinessUnit(
        code="MCC",
        name="Marketing & Client Communications",
        cost_center="CC-4620",
        owner="Sofia Delgado",
        owner_email="sofia.delgado@example.com",
        owner_phone="(212) 555-0131",
        monthly_budget=Decimal("1200"),
        baseline_units=88_000,
        monthly_growth=0.02,
        workloads=(
            Workload("gpt-4.1", 0.70, 3_400, 980, 0.12),
            Workload("gpt-5.4-mini", 0.30, 3_000, 860, 0.20),
            Workload("text-embedding-3-small", 0.40, 900, 0, 0.0),
        ),
        description="Campaign copy drafting and client-letter personalisation.",
    ),
    BusinessUnit(
        code="ITS",
        name="Corporate IT Service Desk",
        cost_center="CC-4733",
        owner="Ravi Chandrasekar",
        owner_email="ravi.chandrasekar@example.com",
        owner_phone="(212) 555-0155",
        monthly_budget=Decimal("400"),
        baseline_units=134_000,
        monthly_growth=0.01,
        workloads=(
            Workload("gpt-5.4-mini", 0.88, 2_100, 340, 0.57),
            Workload("gpt-4.1", 0.12, 2_600, 410, 0.15),
            Workload("text-embedding-3-small", 0.85, 540, 0, 0.0),
        ),
        description="Ticket triage, runbook lookup, and first-line response drafting.",
    ),
    BusinessUnit(
        code="ITD",
        name="Institutional Trading Desk",
        cost_center="CC-4850",
        owner="Aiko Tanaka",
        owner_email="aiko.tanaka@example.com",
        owner_phone="(212) 555-0126",
        monthly_budget=Decimal("11500"),
        baseline_units=74_000,
        monthly_growth=0.11,
        workloads=(
            Workload("gpt-5.5", 0.74, 8_900, 1_400, 0.21),
            Workload("gpt-5.4-mini", 0.26, 3_600, 480, 0.16),
            Workload("text-embedding-3-large", 0.70, 1_800, 0, 0.0),
        ),
        description="Pre-trade research assembly and post-trade commentary.",
    ),
)

BU_BY_CODE: dict[str, BusinessUnit] = {bu.code: bu for bu in BUSINESS_UNITS}

# ── Staged events ────────────────────────────────────────────────────────────
# Two deliberate discontinuities. Both are load-bearing for the evaluation:
# an agent that answers "why did spend move" by pattern-matching on the trend
# rather than reading the incident review will get them wrong.

ANOMALY_MONTH = "2026-02"
ANOMALY_BU = "CSV"
ANOMALY_MODEL = "gpt-5.5"
ANOMALY_CALL_FACTOR = 2.6
ANOMALY_OUTPUT_FACTOR = 4.3
ANOMALY_INCIDENT_ID = "MAP-INC-2026-0214"

# MCC completes its gpt-4.1 exit in January: the legacy share moves to
# gpt-5.4-mini. Spend falls while volume rises, which is the opposite of the
# naive expectation.
MIGRATION_MONTH = "2026-01"
MIGRATION_BU = "MCC"
MIGRATION_FROM = "gpt-4.1"
MIGRATION_TO = "gpt-5.4-mini"


def _fraction(key: str) -> float:
    """Stable [0, 1) fraction from a key. Replaces a seeded PRNG so the data is
    reproducible across interpreters, not merely across runs on one machine."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:6], "big") / float(1 << 48)


def _jitter(key: str, low: float, high: float) -> float:
    return low + _fraction(key) * (high - low)


def _round_tokens(value: float) -> int:
    """Tokens are reported to the nearest thousand.

    The rendered figure and the billed figure must be the same number — if the
    document showed 48,117,412 and the cost was computed from 48,117,412 while
    the table rounded to 48.1M, nobody reading the page could check the
    arithmetic, and the whole dataset would be ungradeable.
    """
    return int(round(value / 1_000.0)) * 1_000


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class UsageRow:
    month: str
    bu_code: str
    model: str
    requests: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    cost: Decimal

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.cached_input_tokens + self.output_tokens


def _workloads_for(bu: BusinessUnit, month: str) -> tuple[Workload, ...]:
    """Apply the MCC legacy-model migration from its effective month onward."""
    if bu.code != MIGRATION_BU or month < MIGRATION_MONTH:
        return bu.workloads

    moved: list[Workload] = []
    legacy_share = 0.0
    for workload in bu.workloads:
        if workload.model == MIGRATION_FROM:
            legacy_share = workload.calls_per_unit
            continue
        moved.append(workload)

    merged: list[Workload] = []
    for workload in moved:
        if workload.model == MIGRATION_TO:
            merged.append(
                Workload(
                    model=workload.model,
                    calls_per_unit=round(workload.calls_per_unit + legacy_share, 4),
                    avg_input_tokens=workload.avg_input_tokens,
                    avg_output_tokens=workload.avg_output_tokens,
                    cache_hit_rate=workload.cache_hit_rate,
                )
            )
        else:
            merged.append(workload)
    return tuple(merged)


def cost_for(
    month: str, model: str, input_tokens: int, cached_tokens: int, output_tokens: int
) -> Decimal:
    """Price tokens with the card in effect for `month`, not the current card."""
    card = rate_card_for(month)
    rate_in, rate_cached, rate_out = card.rates[model]
    total = (
        Decimal(input_tokens) * rate_in
        + Decimal(cached_tokens) * rate_cached
        + Decimal(output_tokens) * rate_out
    ) / MILLION
    return _money(total)


def usage_rows() -> list[UsageRow]:
    """The whole fact table. 8 business units x 6 months x their model mix."""
    rows: list[UsageRow] = []

    for bu in BUSINESS_UNITS:
        for index, month in enumerate(MONTHS):
            growth = (1.0 + bu.monthly_growth) ** index
            seasonal = _jitter(f"{bu.code}|{month}|volume", 0.93, 1.07)
            units = bu.baseline_units * growth * seasonal

            for workload in _workloads_for(bu, month):
                calls = units * workload.calls_per_unit
                avg_out = float(workload.avg_output_tokens)

                if (
                    bu.code == ANOMALY_BU
                    and month == ANOMALY_MONTH
                    and workload.model == ANOMALY_MODEL
                ):
                    calls *= ANOMALY_CALL_FACTOR
                    avg_out *= ANOMALY_OUTPUT_FACTOR

                requests = int(round(calls))
                gross_input = calls * workload.avg_input_tokens
                cached = _round_tokens(gross_input * workload.cache_hit_rate)
                uncached = _round_tokens(gross_input) - cached
                output = _round_tokens(calls * avg_out)

                rows.append(
                    UsageRow(
                        month=month,
                        bu_code=bu.code,
                        model=workload.model,
                        requests=requests,
                        input_tokens=uncached,
                        cached_input_tokens=cached,
                        output_tokens=output,
                        cost=cost_for(month, workload.model, uncached, cached, output),
                    )
                )

    return rows


def billed_amount(metered: Decimal) -> Decimal:
    """Metered consumption plus the platform uplift. What the cost centre pays."""
    return _money(metered * (Decimal(1) + PLATFORM_UPLIFT))


class Facts:
    """Query surface over the fact table. Every document renders from this."""

    def __init__(self) -> None:
        self.rows = usage_rows()

    def for_month(self, month: str) -> list[UsageRow]:
        return [row for row in self.rows if row.month == month]

    def for_bu_month(self, bu_code: str, month: str) -> list[UsageRow]:
        return [row for row in self.rows if row.bu_code == bu_code and row.month == month]

    def select(
        self,
        *,
        bu_code: str | None = None,
        month: str | None = None,
        model: str | None = None,
    ) -> list[UsageRow]:
        return [
            row
            for row in self.rows
            if (bu_code is None or row.bu_code == bu_code)
            and (month is None or row.month == month)
            and (model is None or row.model == model)
        ]

    def cost(self, **filters: str | None) -> Decimal:
        return _money(sum((row.cost for row in self.select(**filters)), Decimal(0)))

    def tokens(self, **filters: str | None) -> int:
        return sum(row.total_tokens for row in self.select(**filters))

    def requests(self, **filters: str | None) -> int:
        return sum(row.requests for row in self.select(**filters))

    def billed(self, *, bu_code: str | None = None, month: str | None = None) -> Decimal:
        """Billed cost, always summed from per-cost-centre amounts.

        The uplift is applied and rounded per cost centre, because that is where
        the charge is actually posted. Applying it to an aggregate instead
        produces a figure that differs from the sum of the statements by a cent
        or two — which is exactly the kind of discrepancy an agent asked to
        reconcile two documents will find and report, correctly, as an error.
        There is one rule and it lives here.
        """
        codes = [bu_code] if bu_code else [bu.code for bu in BUSINESS_UNITS]
        return _money(
            sum((billed_amount(self.cost(bu_code=code, month=month)) for code in codes), Decimal(0))
        )

    def breaches(self) -> list[tuple[str, str, Decimal, Decimal]]:
        """(month, bu_code, billed, budget) where billed exceeded budget."""
        found: list[tuple[str, str, Decimal, Decimal]] = []
        for month in MONTHS:
            for bu in BUSINESS_UNITS:
                billed = self.billed(bu_code=bu.code, month=month)
                if billed > bu.monthly_budget:
                    found.append((month, bu.code, billed, bu.monthly_budget))
        return found
