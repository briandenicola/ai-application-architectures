"""Agent parity contract.

The demo claims that the only difference between a failing agent and a passing
agent is the prompt and the retrieval configuration. These tests make that claim
falsifiable. If someone quietly upgrades v2's model or raises its temperature, the
comparison stops being honest and this suite fails.
"""

from __future__ import annotations

import yaml
from conftest import AGENTS_DIR

V1 = AGENTS_DIR / "v1-naive.agent.yaml"
V2 = AGENTS_DIR / "v2-hardened.agent.yaml"

ALLOWED_DIFFERENCES = {"name", "description", "instructions", "knowledge"}


def load(path):
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_both_definitions_exist():
    assert V1.exists() and V2.exists()


def test_models_are_identical():
    v1, v2 = load(V1), load(V2)
    assert v1["model"] == v2["model"], (
        "v1 and v2 must use an identical model block — same deployment, version, "
        "temperature, top_p and seed. Otherwise the evaluation compares models, "
        "not prompts, and the demo's central claim is false."
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


def test_both_are_prompt_agents():
    for path in (V1, V2):
        assert load(path)["kind"] == "prompt", f"{path.name} must be a prompt agent"


def test_reproducibility_is_configured():
    """Reasoning models reject temperature/top_p/seed, so the pinned model
    version is the reproducibility lever. If a sampling knob IS declared it must
    be the deterministic value, otherwise the claim is decorative."""
    for path in (V1, V2):
        model = load(path)["model"]
        assert model["version"] != "latest", f"{path.name}: model version must be pinned"
        if "temperature" in model:
            assert model["temperature"] == 0.0, f"{path.name}: temperature must be 0.0"
        if "top_p" in model:
            assert model["top_p"] == 1.0, f"{path.name}: top_p must be 1.0"


def test_v1_is_genuinely_ungoverned():
    """If v1 accidentally acquires guards it will pass the gate and the demo dies."""
    instructions = load(V1)["instructions"].lower()
    for forbidden in ("cite", "citation", "disclosure", "effective date", "never"):
        assert forbidden not in instructions, (
            f"v1 instructions contain '{forbidden}' — v1 must have no guards, "
            "otherwise it may pass the gate and the v1/v2 contrast collapses."
        )
    assert load(V1)["knowledge"]["retrieval"]["include_citations"] is False


def test_v2_contains_all_five_guards():
    instructions = load(V2)["instructions"]
    for guard in (
        "GUARD 1 — Grounding",
        "GUARD 2 — Citation",
        "GUARD 3 — Recency",
        "GUARD 4 — Required disclosure",
        "GUARD 5 — Boundaries",
    ):
        assert guard in instructions, f"v2 is missing {guard}"
    assert load(V2)["knowledge"]["retrieval"]["include_citations"] is True
