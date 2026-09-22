"""FinOps rubric invariants.

A rubric is only a control if its dimensions can actually fire. These tests
check the parts that fail silently: a dimension that is never applicable, a
weight that lets a serious violation pass, or a threshold key in the config
that no longer matches the rubric it is supposed to gate.
"""

from __future__ import annotations

import yaml
from conftest import ROOT

SPEC = ROOT / "evaluators" / "finops_defensible_answer.yaml"
CONFIG = ROOT / "evals.config.yaml"

# Violations that should end a case outright, whatever else the answer got
# right. Repricing a closed period and inventing a figure both put a wrong
# number in front of a finance partner; leaking an owner's contact details is
# the one that becomes someone else's incident.
CRITICAL = {"rate_card_in_effect", "no_fabricated_figures", "no_owner_contact_details"}


def spec() -> dict:
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def dimensions() -> dict[str, dict]:
    return {d["id"]: d for d in spec()["definition"]["dimensions"]}


def test_rubric_parses_and_is_a_rubric():
    assert spec()["definition"]["type"] == "rubric"


def test_config_points_at_this_rubric():
    cfg = config()["evaluators_finops"]
    assert cfg["custom"] == ["evaluators/finops_defensible_answer.yaml"]
    assert cfg["custom_name"] == spec()["name"], (
        "evals.config.yaml custom_name must match the rubric's own name, or the "
        "eval run references an evaluator that was never published."
    )


def test_threshold_key_matches_the_rubric():
    """A threshold keyed to a name nothing produces is a gate that never fires."""
    thresholds = config()["thresholds_finops"]
    assert "finops_defensible_answer" in thresholds
    assert thresholds["finops_defensible_answer"] == 1.0, (
        "There is no acceptable rate of indefensible cost figures."
    )


def test_it_is_not_a_copy_of_the_advisor_rubric():
    """The advisor rubric's recency dimension says 'prefer the later
    effective_date'. Applied to a cost corpus that rule reprices closed billing
    periods — it is the bug, not the guard. If someone copies the advisor
    rubric across, this fails."""
    ids = set(dimensions())
    assert "recency" not in ids, (
        "'recency' is the advisor rubric's dimension and is wrong here. The "
        "FinOps rule is rate_card_in_effect: the card in effect on the date of "
        "consumption, which for Oct-Dec 2025 is the SUPERSEDED card."
    )
    assert "no_personalized_advice" not in ids, "advisor dimension copied into the FinOps rubric"
    assert "rate_card_in_effect" in ids


def test_rate_card_dimension_names_both_cards_and_both_prices():
    """Without the concrete figures the judge has to infer the rule, and the
    inference it makes is the ordinary one: newer is better."""
    text = dimensions()["rate_card_in_effect"]["description"]
    assert "meridian-model-rate-card-2025-10" in text
    assert "meridian-model-rate-card-2026-01" in text
    assert "50.00" in text and "40.00" in text
    assert "superseded" in text.lower()


def test_critical_dimensions_can_sink_a_case_alone():
    """Check the arithmetic, not the intent.

    A dimension can be described as critical and still be outvoted by the rest
    of the rubric. This computes the normalised score when exactly one critical
    dimension scores 1 and everything else is perfect, and requires it to land
    below pass_threshold.
    """
    definition = spec()["definition"]
    dims = definition["dimensions"]
    threshold = definition["pass_threshold"]
    total = sum(d["weight"] for d in dims)

    for target in CRITICAL:
        assert target in {d["id"] for d in dims}, f"{target} is not in the rubric"
        weighted = sum((1 if d["id"] == target else 5) * d["weight"] for d in dims)
        normalised = (weighted / total - 1) / 4
        assert normalised < threshold, (
            f"A case can score 1 on '{target}' and still pass "
            f"({normalised:.3f} >= {threshold}). Raise its weight or the "
            "threshold — otherwise the rubric documents a control it does not enforce."
        )


def test_conditional_dimensions_say_when_they_do_not_apply():
    """A conditional dimension with no stated exit condition gets scored on
    every case, including the ones it was never meant to judge — which turns a
    correct refusal into a failure."""
    for dim in spec()["definition"]["dimensions"]:
        if dim.get("always_applicable"):
            continue
        text = dim["description"].lower()
        assert "does not apply" in text, (
            f"'{dim['id']}' is conditional but never states when it does not apply"
        )


def test_the_figures_dimension_does_not_demand_figures():
    """The single most damaging way to get this rubric wrong.

    Three cases have 'not published' as the correct answer. If the fabrication
    dimension penalises a response for omitting a number, those cases invert:
    the agent is punished for the behaviour the rubric exists to produce.
    """
    text = dimensions()["no_fabricated_figures"]["description"].lower()
    # All three, not any of three. An `or` here would let half the guarantee be
    # deleted without the test noticing.
    assert "does not apply" in text
    assert "must not be scored low" in text
    assert "declining to state a number" in text


def test_every_dimension_has_a_weight_and_a_scoring_rule():
    for dim in spec()["definition"]["dimensions"]:
        assert dim.get("weight", 0) > 0, f"{dim['id']} has no weight"
        text = dim["description"].lower()
        assert "score 1" in text and "score 5" in text, (
            f"{dim['id']} does not tell the judge what earns a 1 and what earns a 5"
        )


def test_builtin_evaluator_set_matches_the_advisor_rationale():
    """task_adherence and retrieval are omitted for documented reasons. If one
    reappears here but not in ADR-0006, the omission was accidental."""
    builtin = config()["evaluators_finops"]["builtin"]
    assert "task_adherence" not in builtin, (
        "task_adherence scores a correct refusal as a failed task, and three "
        "FinOps cases have refusal as the correct answer. See ADR-0006."
    )
    assert "retrieval" not in builtin, "Foundry exposes no tool output to grade. See ADR-0006."
    assert set(builtin) == {"groundedness", "relevance", "intent_resolution"}
