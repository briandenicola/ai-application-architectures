"""The gate is only meaningful if every threshold is reachable.

A threshold outside its metric's scale fails 100% of cases and is
indistinguishable from a genuine regression. That cost a full evaluation run to
spot once, when task_adherence was scored 0/1 by the local SDK while every other
metric was 1-5. Foundry scores it 1-5, but the lesson stands: these tests make
that class of mistake fail in CI instead, for free.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_eval import BUILTIN_EVALUATORS, check_thresholds  # noqa: E402


@pytest.fixture(scope="module")
def config() -> dict:
    raw = yaml.safe_load((ROOT / "evals.config.yaml").read_text(encoding="utf-8"))
    return raw


def test_every_configured_threshold_is_reachable(config: dict) -> None:
    assert check_thresholds(config) == []


def test_every_configured_evaluator_has_a_threshold(config: dict) -> None:
    configured = set(config["evaluators"]["builtin"])
    configured.add("compliance_safe_answer")
    missing = configured - set(config["thresholds"])
    assert not missing, f"No threshold set for: {sorted(missing)}"


def test_unreachable_threshold_is_rejected(config: dict) -> None:
    """The check must actually catch the bug it exists to catch."""
    broken = {**config, "thresholds": {**config["thresholds"], "task_adherence": 9.0}}
    problems = check_thresholds(broken)
    assert any("task_adherence" in problem for problem in problems)


def test_scales_match_the_foundry_evaluator_catalog() -> None:
    """Mirrors the declared metric ranges in the catalog.

    task_adherence is the odd one out: the catalog declares it boolean while its
    threshold parameter claims 1-5. Trusting the threshold parameter fails every
    case. run_eval.verify_scales() re-checks this live on every run.
    """
    expected = {
        "groundedness": (1, 5),
        "relevance": (1, 5),
        "intent_resolution": (1, 5),
        "task_adherence": (0, 1),
    }
    for name, (_evaluator, _mapping, scale) in BUILTIN_EVALUATORS.items():
        assert scale == expected[name], f"{name} scale drifted from the catalog"


def test_groundedness_is_given_a_context_to_judge_against() -> None:
    """Groundedness with no context silently grades nothing and still returns a
    score, which reads as a passing grounded answer when nothing was grounded."""
    mapping = BUILTIN_EVALUATORS["groundedness"][1]
    assert mapping.get("context"), "groundedness must be mapped to a context"


def test_retrieval_is_not_configured() -> None:
    """Foundry exposes no tool outputs to evaluators, so retrieval has nothing
    to grade. Re-adding it would score the golden set, not the agent."""
    assert "retrieval" not in BUILTIN_EVALUATORS
