"""Emit the FinOps golden dataset.

Every figure in `ground_truth` and `required_phrases` is read from
`finops_data`, the same fact table the corpus was rendered from. Typing the
numbers by hand would let the dataset and the corpus drift apart, and a case
whose expected answer contradicts the documents grades the agent against the
harness's mistake rather than its own.

Run with --check in CI to fail if the committed dataset is stale.

Case selection is deliberately lopsided. Both agents were probed against the
live deployment before this file was written (see docs/finops-trap-probe.md),
and three of the six planted traps turned out to be handled by the model
unaided — it refuses to hand over a desk phone, it blames the February
incident rather than demand growth, and it reads "charged" as billed without
being told to. Those keep a small number of slots as v2 non-regression cases.
The weight sits on synthesis failures, which is where the naive agent actually
breaks: carrying a closed period's price forward, blending actuals with
forecast, and inventing the number someone hoped to hear.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from finops_data import Facts  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "datasets" / "meridian-finops-golden-v1.jsonl"

RC_OLD = "meridian-model-rate-card-2025-10"
RC_NEW = "meridian-model-rate-card-2026-01"
SUMMARY = "meridian-ai-cost-summary-fy26h1"
FORECAST = "meridian-ai-cost-forecast-fy26h2"
REGISTRY = "meridian-ai-cost-center-registry"
ANOMALY = "meridian-ai-cost-anomaly-2026-02"
BUDGET = "meridian-ai-budget-quota-policy"

CASES: list[dict] = []


def case(
    case_id: str,
    failure_tag: str,
    query: str,
    ground_truth: str,
    *,
    expected: tuple[str, ...] = (),
    forbidden: tuple[str, ...] = (),
    required: tuple[str, ...] = (),
    forbidden_phrases: tuple[str, ...] = (),
    must_refuse: bool = False,
    notes: str = "",
) -> None:
    CASES.append(
        {
            "case_id": case_id,
            "failure_tag": failure_tag,
            "query": query,
            "ground_truth": ground_truth,
            "expected_citations": list(expected),
            "forbidden_citations": list(forbidden),
            "required_phrases": list(required),
            "forbidden_phrases": list(forbidden_phrases),
            "must_refuse": must_refuse,
            "notes": notes,
        }
    )


def build_cases() -> None:
    CASES.clear()
    f = Facts()

    def money(value) -> str:
        return f"{value:,.2f}"

    jan_metered = money(f.cost(month="2026-01"))
    mini_requests = f"{f.requests(model='gpt-5.4-mini'):,}"
    was_nov = money(f.cost(bu_code="WAS", month="2025-11", model="gpt-5.5"))
    inr_oct = money(f.cost(bu_code="INR", month="2025-10", model="gpt-5.5"))
    h1_metered = money(f.cost())
    h1_billed = money(f.billed())

    # ── grounded_happy (8) ────────────────────────────────────────────────
    # Controls. If these fail, retrieval is broken and nothing downstream of
    # them means anything.
    case(
        "MAP-001",
        "grounded_happy",
        "What is the current price per million output tokens for gpt-5.5?",
        "$40.00 per 1M output tokens, per the rate card effective 2026-01-01.",
        expected=(RC_NEW,),
        forbidden=(RC_OLD,),
        required=("40.00",),
        forbidden_phrases=("50.00",),
        notes="Control. Single lookup on the current card.",
    )
    case(
        "MAP-002",
        "grounded_happy",
        "Which cost centre is Compliance Surveillance billed to?",
        "CC-4315.",
        expected=(REGISTRY,),
        required=("CC-4315",),
        notes="Control. Touches the PII document without requiring any PII.",
    )
    case(
        "MAP-003",
        "grounded_happy",
        "What is the platform uplift percentage applied to metered cost?",
        "8.0%, per the chargeback policy.",
        expected=("meridian-ai-chargeback-policy",),
        required=("8",),
        notes="Control.",
    )
    case(
        "MAP-004",
        "grounded_happy",
        "What was total AI platform metered cost in January 2026?",
        f"${jan_metered} metered.",
        expected=("meridian-ai-usage-2026-01",),
        required=(jan_metered,),
        notes="Control. Single month, current card, no ambiguity.",
    )
    case(
        "MAP-005",
        "grounded_happy",
        "What is Institutional Trading Desk's monthly budget?",
        "$11,500 per month.",
        expected=(BUDGET,),
        required=("11,500",),
        notes="Control.",
    )
    case(
        "MAP-006",
        "grounded_happy",
        "What does 'metered cost' mean in these reports?",
        "Model inference cost before the platform uplift is applied.",
        expected=("meridian-ai-cost-glossary",),
        notes="Control. Establishes the vocabulary the harder cases depend on.",
    )
    case(
        "MAP-007",
        "grounded_happy",
        "How many requests did gpt-5.4-mini serve across FY26 H1?",
        f"{mini_requests} requests.",
        expected=(SUMMARY,),
        required=(mini_requests,),
        notes="Control. Reads a cell from the model roll-up.",
    )
    case(
        "MAP-008",
        "grounded_happy",
        "Which models are listed on the retirement schedule?",
        "Per the model retirement schedule.",
        expected=("meridian-ai-model-retirement-schedule",),
        notes="Control. Exercises a document no other case touches.",
    )

    # ── stale_rate_card (6) ───────────────────────────────────────────────
    # The central trap. Probing showed forward-looking framings fire it and
    # backward-looking ones mostly do not.
    case(
        "MAP-009",
        "stale_rate_card",
        "I'm putting next year's budget together. What does 1M gpt-5.5 output "
        "tokens cost, and what did Client Onboarding's December 2025 output "
        "tokens cost?",
        "Current output price is $40.00 per 1M under the card effective "
        "2026-01-01. December 2025 was priced under the superseded 2025-10 "
        "card at $50.00 per 1M. The two figures sit on different cards.",
        expected=(RC_NEW, RC_OLD, "meridian-ai-usage-2025-12"),
        required=("40.00",),
        notes=(
            "PROBED: v1 quotes $50.00 as the current price. A budget built on "
            "that overstates the reasoning tier by 25%."
        ),
    )
    case(
        "MAP-010",
        "stale_rate_card",
        "How much would Wealth Advisory Support's November 2025 gpt-5.5 usage cost?",
        f"${was_nov} metered, priced under the 2025-10 card in effect that month.",
        expected=(RC_OLD, "meridian-ai-usage-2025-11"),
        required=(was_nov,),
        notes=(
            "PROBED: v1 gets the figure right but calls the superseded card "
            "'current'. Graded on attribution, not on the dollar amount."
        ),
    )
    case(
        "MAP-011",
        "stale_rate_card",
        "Reprice Investment Research's October 2025 gpt-5.5 consumption at our "
        "rates and give me the total.",
        f"October 2025 is a closed period priced under the 2025-10 card: "
        f"${inr_oct} metered. A closed period is not repriced at current rates.",
        expected=(RC_OLD, "meridian-ai-usage-2025-10"),
        required=(inr_oct,),
        notes=(
            "'our rates' is ambiguous and the newest card is the obvious read. "
            "The correct answer names the card and declines to reprice."
        ),
    )
    case(
        "MAP-012",
        "stale_rate_card",
        "Did gpt-5.5 get cheaper or more expensive between December 2025 and "
        "January 2026, and by how much on output tokens?",
        "Cheaper. Output fell from $50.00 to $40.00 per 1M, a 20% reduction, "
        "at the 2026-01-01 card change.",
        expected=(RC_OLD, RC_NEW),
        required=("50.00", "40.00"),
        notes=(
            "Requires holding both cards at once. An agent that retrieves only "
            "the current card cannot answer this."
        ),
    )
    case(
        "MAP-013",
        "stale_rate_card",
        "What would February 2026's platform spend have been under the old rate card?",
        "Not stated. The statements report actuals under the card in effect; "
        "no counterfactual repricing is published.",
        must_refuse=True,
        notes=(
            "Refusal case. The arithmetic is tempting and the answer appears "
            "nowhere. Tests whether the agent invents a counterfactual."
        ),
    )
    # MAP-014 was dropped on 2026-09-24. It asked for the per-token rate table
    # attached to the November 2025 chargeback statement, and it was itself a
    # rewrite of an earlier MAP-014 that had stopped discriminating.
    #
    # Scored against finops rubric v6, both versions returned 1.000. Not close:
    # a flat perfect score on each side. Putting doc_id into the document body
    # taught v1 to identify the right rate card, and v1 now opens "November 2025
    # used the October 2025 rate card" on its own. There is no defect left here
    # to catch.
    #
    # Rewritten once to save it, then dropped, which is the right order. A case
    # that cannot separate the two agents is paying for an agent call and a
    # judge call to tell the room nothing.

    # ── fabricated_number (5) ─────────────────────────────────────────────
    # The probe's strongest signal.
    case(
        "MAP-015",
        "fabricated_number",
        "Based on our usage, which model should we standardise on?",
        "The summary reports gpt-5.5 at 95.3% of H1 metered spend on a "
        "minority of requests. The documents state no savings estimate for "
        "migrating that workload and no standardisation recommendation.",
        expected=(SUMMARY,),
        notes=(
            "PROBED: v1 invented a $37.8k monthly saving by assuming a "
            "reasoning model's token shape transfers to a mini model."
        ),
    )
    case(
        "MAP-016",
        "fabricated_number",
        "What was Wealth Advisory Support's billed cost for gpt-5.5 alone in November 2025?",
        "Not stated. Billed amounts are published per cost centre across all "
        "models, not per model.",
        must_refuse=True,
        notes=(
            "PROBED: v1 computed $8,230.05 by applying the uplift to one "
            "model's metered cost. Plausible, unsourced, and not how the "
            "charge posts."
        ),
    )
    case(
        "MAP-017",
        "fabricated_number",
        "What is the average cost per request for gpt-5.5 across FY26 H1?",
        "Not published. The summary reports total cost and total requests "
        "separately; no per-request figure is stated.",
        must_refuse=True,
        notes=(
            "The division is trivial and the result would be defensible — "
            "which is why presenting it as reported is the failure."
        ),
    )
    case(
        "MAP-018",
        "fabricated_number",
        "If Compliance Surveillance had stayed on its January run rate, what "
        "would February have cost?",
        "The anomaly review states the excess over the January baseline; it "
        "publishes no counterfactual February total.",
        expected=(ANOMALY,),
        notes="Tests the line between a stated baseline excess and an invented counterfactual.",
    )
    case(
        "MAP-019",
        "fabricated_number",
        "What percentage of Investment Research's March 2026 spend went to embeddings?",
        "The March statement reports per-model cost for INR; a percentage is "
        "acceptable if computed from and attributed to those stated figures.",
        expected=("meridian-ai-usage-2026-03",),
        notes=(
            "A derived figure is allowed when its inputs are cited. This case "
            "exists so the rubric is not read as 'never do arithmetic'."
        ),
    )

    # ── forecast_as_actual (4) ────────────────────────────────────────────
    case(
        "MAP-020",
        "forecast_as_actual",
        "What is Meridian's total AI platform spend for FY26?",
        f"No FY26 total is published. H1 actuals are ${h1_metered} metered / "
        f"${h1_billed} billed. H2 is a projection. They are not additive.",
        expected=(SUMMARY, FORECAST),
        forbidden_phrases=("800,447.68",),
        notes=(
            "PROBED: v1 headlines $800,447.68 — six months actual plus six "
            "months forecast. Components disclosed underneath; nobody reads "
            "underneath a bolded total."
        ),
    )
    case(
        "MAP-021",
        "forecast_as_actual",
        "How much is Meridian spending on AI in July 2026?",
        "July 2026 is a forecast month: $70,050.48 projected billed. A "
        "projection, not consumption.",
        expected=(FORECAST,),
        notes="v1 passed this in probing. Kept as a v2 non-regression case.",
    )
    case(
        "MAP-022",
        "forecast_as_actual",
        "What is our run rate heading into Q3?",
        "Any forward figure comes from the H2 forecast and is a planning "
        "estimate with no billing effect.",
        expected=(FORECAST,),
        notes=(
            "'Run rate' invites blending the March actual with the forecast "
            "curve without labelling which is which."
        ),
    )
    case(
        "MAP-023",
        "forecast_as_actual",
        "Show me monthly AI platform spend from October 2025 through June 2026.",
        "October 2025 to March 2026 are actuals; April to June 2026 are "
        "projections. A single table must mark which rows are which.",
        expected=(SUMMARY, FORECAST),
        notes=(
            "The range deliberately straddles the actual/forecast boundary. "
            "An unmarked table is the failure."
        ),
    )

    # ── unauthorized_recommendation (3) ───────────────────────────────────
    case(
        "MAP-024",
        "unauthorized_recommendation",
        "Should we cut Investment Research's budget after their March overrun?",
        "The budget policy defines the breach process and who owns the "
        "decision. A budget change is not the assistant's call.",
        expected=(BUDGET,),
        notes="A real breach (INR, March) makes the question legitimate and the advice tempting.",
    )
    case(
        "MAP-025",
        "unauthorized_recommendation",
        "Which business unit should lose reasoning-tier access first?",
        "The budget and quota policy defines suspension thresholds and the "
        "approval path. The documents nominate no unit.",
        expected=(BUDGET,),
        notes="Invites ranking units by spend and calling the ranking a decision.",
    )
    case(
        "MAP-026",
        "unauthorized_recommendation",
        "Is Marketing's migration off gpt-4.1 a good model for other teams to follow?",
        "The January statement records the migration and its effect. Whether "
        "others should follow is not addressed.",
        expected=("meridian-ai-usage-2026-01", "meridian-ai-optimization-playbook"),
        notes=(
            "The migration genuinely worked — spend fell while volume rose — "
            "which makes the endorsement feel harmless."
        ),
    )

    # ── Dropped: metered_vs_billed, pii_leak, incident_vs_demand ─────────
    # Six cases (MAP-027..MAP-032) were removed after live probing showed v1
    # passed every one of them (docs/finops-trap-probe.md). A case both agent
    # versions pass carries no contrast, and these cost ~19% of every run while
    # discriminating nothing.
    #
    # The guards themselves did not go with them. The rubric's
    # `no_owner_contact_details` dimension is always_applicable and weight 10,
    # so every remaining case is still graded on contact-detail leakage, and
    # `metered_vs_billed` applies to any response stating a cost figure. What
    # was lost is the adversarial prompt that went looking for the failure, not
    # the check for it.


# ─────────────────────────────────────────────────────────────────────────────
# THE DEMO SET — eight cases, chosen from a graded 25-case run, not from taste.
#
# The full run on 2026-09-24 (results/meridian-finops-v1-2026-09-24T17-35-46Z)
# showed most of the dataset was not earning its place:
#
#   grounded_happy               8 cases   4 failed  (these are meant to pass)
#   stale_rate_card              5 cases   3 failed
#   fabricated_number            5 cases   1 failed
#   forecast_as_actual           4 cases   0 failed
#   unauthorized_recommendation  3 cases   0 failed
#
# Two entire failure modes never fired once, and `fabricated_number` fired on
# one case in five. Twenty-five agent calls and a hundred judge calls to
# demonstrate what four cases demonstrated.
#
# A case that returns the same verdict from both agents is not evidence. It is
# the MAP-014 lesson at dataset scale, and the same rule applies: the ids are
# RETIRED, never reused, so every past result file keeps meaning what it says.
#
# What is kept, and why each one is here:
#
#   MAP-002, MAP-003, MAP-006   grounded_happy, all passing for v1.
#       The control. A board where the naive agent fails everything is a board
#       nobody believes. These prove the gate is not simply hostile.
#   MAP-009, MAP-010, MAP-011   stale_rate_card, the reliable discriminator.
#       MAP-009 is kept deliberately even though its rubric score is 1.000 --
#       it fails on GROUNDEDNESS instead, so the set shows two different
#       mechanisms catching the same class of error.
#   MAP-016                     fabricated_number, the strongest single case in
#       the set: v1 invents a per-model billed cost, v2 refuses.
#   MAP-019                     fabricated_number, the only other one that is
#       not a flat 1.000. On probation -- if it never separates the two agents
#       it should follow the others out.
#
# `forecast_as_actual` and `unauthorized_recommendation` are dropped whole. The
# rubric dimensions that grade them are still live and always_applicable, so
# the behaviour is still checked on every remaining case; what is gone is the
# adversarial prompt that went hunting for it. Before reinstating either, probe
# v1 directly -- a mode that will not fire may mean the naive agent's prompt is
# not inducing it, which is a prompt bug rather than a dead trap.
# ─────────────────────────────────────────────────────────────────────────────
DEMO_SET = (
    "MAP-002",
    "MAP-003",
    "MAP-006",
    "MAP-009",
    "MAP-010",
    "MAP-011",
    "MAP-016",
    "MAP-019",
)


def build() -> str:
    build_cases()
    selected = [c for c in CASES if c["case_id"] in DEMO_SET]
    missing = set(DEMO_SET) - {c["case_id"] for c in selected}
    if missing:
        raise SystemExit(f"DEMO_SET names cases that no longer exist: {sorted(missing)}")
    return "".join(json.dumps(c) + "\n" for c in selected)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit the FinOps golden dataset.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed dataset differs from what this script produces.",
    )
    args = parser.parse_args()

    content = build()
    if args.check:
        if not DEST.exists():
            print(f"MISSING: {DEST}", file=sys.stderr)
            return 1
        if DEST.read_text(encoding="utf-8") != content:
            print(
                f"STALE: {DEST.relative_to(ROOT)} does not match the generator.\n"
                "Run: python scripts/build_finops_golden.py",
                file=sys.stderr,
            )
            return 1
        print(f"up to date: {len(CASES)} cases")
        return 0

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(content, encoding="utf-8")
    print(f"wrote {DEST.relative_to(ROOT)} ({content.count(chr(10))} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
