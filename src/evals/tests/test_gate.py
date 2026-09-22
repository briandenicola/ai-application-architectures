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


# ─────────────────────────────────────────────────────────────────────────────
# Both tests below were written AFTER the bugs they describe reached a live
# Azure run. The suite was 135 tests green at the time and caught neither,
# because nothing exercised run_eval end to end on a second track. A gate that
# is only tested on one corpus is tested on one corpus.
# ─────────────────────────────────────────────────────────────────────────────


def _real_config(corpus: str) -> dict:
    """The committed config, read WITHOUT ${ENV} resolution.

    load_config() resolves environment placeholders and raises without a
    provisioned azd environment. These tests must run with no Azure, so the
    YAML is read directly — none of the keys under test are templated.
    """
    import yaml
    from _common import select_corpus

    with (ROOT / "evals.config.yaml").open(encoding="utf-8") as handle:
        return select_corpus(yaml.safe_load(handle), corpus)


def test_custom_metric_is_resolved_per_track_not_hard_coded():
    """The rubric metric key must follow --corpus.

    This was a module-level constant pinned to the advisor metric. The FinOps
    run raised KeyError('compliance_safe_answer') against live Azure.
    """
    advisor = run_eval.custom_metric(_real_config("meridian"))
    finops = run_eval.custom_metric(_real_config("finops"))

    assert advisor == "compliance_safe_answer"
    assert finops == "finops_defensible_answer"
    assert advisor != finops, (
        "the two tracks must report under different metric keys — sharing one "
        "would let the FinOps run be gated against the advisor's threshold"
    )


def test_every_tracks_custom_metric_is_actually_gated_on():
    """A rubric scored but absent from thresholds is a rubric nobody gates on.

    That failure is silent and looks exactly like success: the scorecard prints,
    the metric appears, and no threshold is ever compared against it.
    """
    for corpus in ("meridian", "finops"):
        config = _real_config(corpus)
        metric = run_eval.custom_metric(config)
        assert metric in config["thresholds"], (
            f"{corpus}: custom_metric '{metric}' has no threshold entry"
        )


def test_a_missing_custom_metric_key_is_a_config_error_not_a_crash():
    from _common import ConfigError

    config = _real_config("finops")
    del config["evaluators"]["custom_metric"]

    try:
        run_eval.custom_metric(config)
    except ConfigError:
        pass  # ConfigError is routed to exit 2 by __main__.
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"raised {type(exc).__name__}, which exits 1 and reads as a quality "
            "failure. Harness problems must exit 2."
        ) from exc
    else:
        raise AssertionError("a missing custom_metric must not pass silently")


def test_a_harness_crash_exits_2_and_never_1(tmp_path):
    """Exit 1 means the agent failed. Exit 2 means the harness could not run.

    Python exits 1 on an uncaught exception, so a bare traceback out of
    run_eval.py is indistinguishable in CI from a breached threshold. This is
    exactly how the hard-coded custom-metric bug presented against live Azure.

    The crash here is real, not simulated: a config that parses as valid YAML
    but has no `dataset` block, which raises KeyError inside main().
    """
    import subprocess
    import sys

    broken = tmp_path / "broken.yaml"
    broken.write_text("models:\n  judge:\n    deployment: x\n", encoding="utf-8")

    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user input
        [
            sys.executable,
            str(ROOT / "scripts" / "run_eval.py"),
            "--agent",
            "whatever",
            "--config",
            str(broken),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode != 1, (
        "the harness exited 1 for a non-quality failure — a crash is now "
        f"indistinguishable from a failed gate.\nstderr:\n{proc.stderr[-2000:]}"
    )
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}\n{proc.stderr[-2000:]}"
