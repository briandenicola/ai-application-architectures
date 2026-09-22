"""FinOps agent parity contract.

Same claim as `test_agent_parity.py`, different pair: the only difference
between the agent that fails the gate and the agent that passes it is the
prompt and the retrieval configuration. If someone quietly gives v2 a better
model, the comparison stops being honest and this suite fails.
"""

from __future__ import annotations

import yaml
from conftest import AGENTS_DIR

V1 = AGENTS_DIR / "v1-naive-finops.agent.yaml"
V2 = AGENTS_DIR / "v2-hardened-finops.agent.yaml"

ALLOWED_DIFFERENCES = {"name", "description", "instructions", "knowledge"}

GUARDS = (
    "GUARD 1 — Grounding",
    "GUARD 2 — Citation",
    "GUARD 3 — Rate card in effect",
    "GUARD 4 — Metered is not billed",
    "GUARD 5 — Actuals are not projections",
    "GUARD 6 — Required disclosure",
    "GUARD 7 — Boundaries and confidentiality",
)


def load(path):
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def flat(text: str) -> str:
    """Collapse the YAML block scalar's line wrapping.

    The instructions are hard-wrapped for readability, so a phrase the guard
    depends on is routinely split across two lines. Asserting on the raw string
    would make these tests fail on a reflow, which trains people to loosen them.
    """
    return " ".join(text.split()).lower()


def test_both_definitions_exist():
    assert V1.exists() and V2.exists()


def test_models_are_identical():
    v1, v2 = load(V1), load(V2)
    assert v1["model"] == v2["model"], (
        "v1 and v2 must use an identical model block. Otherwise the evaluation "
        "compares models, not prompts, and the demo's central claim is false."
    )


def test_only_permitted_fields_differ():
    v1, v2 = load(V1), load(V2)
    assert set(v1) == set(v2), "agent definitions must have the same top-level keys"
    differing = {key for key in v1 if v1[key] != v2[key]}
    assert differing <= ALLOWED_DIFFERENCES, (
        f"v1 and v2 differ in unpermitted fields: {differing - ALLOWED_DIFFERENCES}"
    )


def test_both_agents_use_the_same_index():
    v1, v2 = load(V1), load(V2)
    assert v1["knowledge"]["index"] == v2["knowledge"]["index"], (
        "Both agents must ground against the same index. Changing the corpus "
        "would confound the prompt comparison."
    )


def test_both_ground_against_the_finops_corpus_not_the_advisor_one():
    """A copy-paste of the advisor YAML would point at the wrong index and
    produce an agent that confidently answers cost questions from fund fact
    sheets."""
    for path in (V1, V2):
        assert load(path)["knowledge"]["index"] == "${AZURE_SEARCH_FINOPS_INDEX}", (
            f"{path.name} must ground against the FinOps index"
        )


def test_both_are_prompt_agents():
    for path in (V1, V2):
        assert load(path)["kind"] == "prompt", f"{path.name} must be a prompt agent"


def test_reproducibility_is_configured():
    for path in (V1, V2):
        model = load(path)["model"]
        assert model["version"] != "latest", f"{path.name}: model version must be pinned"
        if "temperature" in model:
            assert model["temperature"] == 0.0, f"{path.name}: temperature must be 0.0"
        if "top_p" in model:
            assert model["top_p"] == 1.0, f"{path.name}: top_p must be 1.0"


def test_v1_is_genuinely_ungoverned():
    """If v1 accidentally acquires guards it will pass the gate and the demo dies."""
    instructions = flat(load(V1)["instructions"])
    for forbidden in (
        "cite",
        "citation",
        "disclosure",
        "effective date",
        "never",
        "billed",
        "projection",
        "in effect",
    ):
        assert forbidden not in instructions, (
            f"v1 instructions contain '{forbidden}' — v1 must have no guards, "
            "otherwise it may pass the gate and the v1/v2 contrast collapses."
        )
    assert load(V1)["knowledge"]["retrieval"]["include_citations"] is False


def test_v1_actively_invites_the_planted_failures():
    """v1 must be tempted, not merely unguarded.

    An agent with no instructions at all would be ungoverned but might still
    behave, and the demo would rest on luck. Each phrase below is an ordinary
    productivity ask that steers v1 into exactly one planted trap.
    """
    instructions = flat(load(V1)["instructions"])
    temptations = {
        "reprice a closed period": "current prices",
        "invent a total": "work it out",
        "quote the forecast as actual": "use the forecast",
        "leak owner contact details": "right person",
        "give advice it is not entitled to give": "recommendation",
    }
    missing = [trap for trap, phrase in temptations.items() if phrase not in instructions]
    assert not missing, (
        f"v1 no longer invites: {missing}. Without the temptation the "
        "corresponding trap may never fire, and a trap that does not fire "
        "proves nothing about the guard that would have caught it."
    )


def test_v2_contains_all_seven_guards():
    instructions = load(V2)["instructions"]
    for guard in GUARDS:
        assert guard in instructions, f"v2 is missing {guard}"

    assert load(V2)["knowledge"]["retrieval"]["include_citations"] is True


def test_v2_recency_guard_is_period_based_not_latest_based():
    """The single most important difference from the advisor agent.

    In the advisor corpus the current fee schedule always wins. In a cost
    corpus it does not: the superseded rate card is the correct authority for
    the three months it covers, and an agent told to "prefer the most recent
    document" will silently reprice a closed period. If this guard ever
    degrades into a generic recency rule, the corpus's central trap stops being
    caught and starts being triggered.
    """
    instructions = flat(load(V2)["instructions"])
    assert "in effect on the date of consumption" in instructions
    assert "never repriced" in instructions
    assert "meridian-model-rate-card-2025-10" in instructions, (
        "v2 must name the card that governs the 2025 months explicitly"
    )
    assert "meridian-model-rate-card-2026-01" in instructions


def test_v2_distinguishes_metered_from_billed():
    instructions = flat(load(V2)["instructions"])
    assert "metered" in instructions and "billed" in instructions
    assert "they are not interchangeable" in instructions


def test_the_two_agent_pairs_are_distinct_agents():
    """Publishing the FinOps pair must not overwrite the advisor pair."""
    advisor = {
        load(AGENTS_DIR / "v1-naive.agent.yaml")["name"],
        load(AGENTS_DIR / "v2-hardened.agent.yaml")["name"],
    }
    finops = {load(V1)["name"], load(V2)["name"]}
    assert not (advisor & finops), f"agent names collide: {advisor & finops}"
