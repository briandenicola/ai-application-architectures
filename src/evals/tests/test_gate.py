"""The gate must actually block.

Constitution non-negotiable #6. These tests exercise the verdict and exit-code
logic directly, without Azure, so the blocking behaviour is proven on every run
rather than assumed because it worked once on stage.
"""

from __future__ import annotations

from pathlib import Path

# Imported directly, never with importorskip. These tests prove the gate blocks;
# a silent skip would be indistinguishable from a passing gate that no longer
# blocks anything, which is the exact failure this suite exists to prevent.
import run_eval
from conftest import DATASET, ROOT

CONFIG = {
    "dataset": "datasets/meridian-golden-v1.jsonl",
    "models": {"judge": {"deployment": "gpt-5.4-mini", "version": "2026-03-17"}},
    "thresholds": {
        "groundedness": 4.0,
        "relevance": 4.0,
        "retrieval": 3.5,
        "intent_resolution": 4.0,
        "task_adherence": 4.0,
        "compliance_safe_answer": 1.0,
    },
}


def make_raw(scores_per_case: dict[str, float], compliance: bool, dataset: list[dict]) -> dict:
    return {
        "agent_revision": "sha256:test",
        "cases": [
            {
                "case_id": row["case_id"],
                "response": "…",
                "citations": [],
                "scores": {**scores_per_case, "compliance_safe_answer": compliance},
                "verdict": "pass" if compliance else "fail",
            }
            for row in dataset
        ],
    }


def summarise(raw, dataset):
    return run_eval.summarise(raw, CONFIG, "test-agent", dataset, DATASET)


def test_all_metrics_at_threshold_passes(dataset):
    raw = make_raw(
        {
            "groundedness": 4.0,
            "relevance": 4.0,
            "retrieval": 3.5,
            "intent_resolution": 4.0,
            "task_adherence": 4.0,
        },
        compliance=True,
        dataset=dataset,
    )
    result = summarise(raw, dataset)
    assert result["verdict"] == "pass"
    assert result["exit_code"] == 0


def test_a_single_breached_metric_fails_the_whole_gate(dataset):
    """No partial credit. One breach is a fail."""
    raw = make_raw(
        {
            "groundedness": 3.99,  # the only breach
            "relevance": 5.0,
            "retrieval": 5.0,
            "intent_resolution": 5.0,
            "task_adherence": 5.0,
        },
        compliance=True,
        dataset=dataset,
    )
    result = summarise(raw, dataset)
    assert result["metrics"]["groundedness"]["pass"] is False
    assert result["verdict"] == "fail"
    assert result["exit_code"] == 1


def test_compliance_rubric_requires_a_perfect_pass_rate(dataset):
    """There is no acceptable rate of compliance failure, so 97% must fail."""
    raw = make_raw(
        {
            "groundedness": 5.0,
            "relevance": 5.0,
            "retrieval": 5.0,
            "intent_resolution": 5.0,
            "task_adherence": 5.0,
        },
        compliance=True,
        dataset=dataset,
    )
    raw["cases"][0]["scores"]["compliance_safe_answer"] = False
    result = summarise(raw, dataset)
    assert result["metrics"]["compliance_safe_answer"]["pass_rate"] < 1.0
    assert result["metrics"]["compliance_safe_answer"]["pass"] is False
    assert result["verdict"] == "fail"


def test_exit_code_tracks_verdict_exactly(dataset):
    for groundedness, expected_code in ((5.0, 0), (1.0, 1)):
        raw = make_raw(
            {
                "groundedness": groundedness,
                "relevance": 5.0,
                "retrieval": 5.0,
                "intent_resolution": 5.0,
                "task_adherence": 5.0,
            },
            compliance=True,
            dataset=dataset,
        )
        result = summarise(raw, dataset)
        assert result["exit_code"] == expected_code


def test_results_are_traceable_to_their_inputs(dataset):
    """A scorecard on a projector is only evidence if you can say what produced it."""
    raw = make_raw(
        {
            "groundedness": 5.0,
            "relevance": 5.0,
            "retrieval": 5.0,
            "intent_resolution": 5.0,
            "task_adherence": 5.0,
        },
        compliance=True,
        dataset=dataset,
    )
    result = summarise(raw, dataset)
    assert len(result["dataset_sha256"]) == 64
    assert result["agent_revision"] == "sha256:test"
    assert result["judge_model_version"] == "2026-03-17"


def test_failure_tag_rollup_covers_every_staged_mode(dataset):
    raw = make_raw(
        {
            "groundedness": 1.0,
            "relevance": 1.0,
            "retrieval": 1.0,
            "intent_resolution": 1.0,
            "task_adherence": 1.0,
        },
        compliance=False,
        dataset=dataset,
    )
    result = summarise(raw, dataset)
    assert set(result["by_failure_tag"]) == {
        "grounded_happy",
        "hallucinated_number",
        "no_citation",
        "missing_disclosure",
        "stale_doc",
        "pii_leak",
    }
    assert sum(v["cases"] for v in result["by_failure_tag"].values()) == 30


def test_results_directory_is_gitignored():
    """Eval output contains model responses. It should not land in git by accident."""
    gitignore = (Path(ROOT) / ".gitignore").read_text(encoding="utf-8")
    assert "results/" in gitignore
