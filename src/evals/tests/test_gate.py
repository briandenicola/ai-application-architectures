"""The gate must actually block.

Constitution non-negotiable #6. These tests exercise the verdict and exit-code
logic directly, without Azure, so the blocking behaviour is proven on every run
rather than assumed because it worked once on stage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Imported directly, never with importorskip. These tests prove the gate blocks;
# a silent skip would be indistinguishable from a passing gate that no longer
# blocks anything, which is the exact failure this suite exists to prevent.
import run_eval
from conftest import DATASET, ROOT

CONFIG = {
    "dataset": "datasets/meridian-golden-v1.jsonl",
    "models": {"judge": {"deployment": "gpt-5.4-mini", "version": "2026-03-17"}},
    "evaluators": {"custom_metric": "compliance_safe_answer"},
    "thresholds": {
        "groundedness": 4.0,
        "relevance": 4.0,
        "retrieval": 3.5,
        "intent_resolution": 4.0,
        "task_adherence": 4.0,
        "compliance_safe_answer": 1.0,
    },
}

BUILTINS = ("groundedness", "relevance", "retrieval", "intent_resolution", "task_adherence")


def make_raw(
    verdicts_per_case: dict[str, bool],
    compliance: bool,
    dataset: list[dict],
    scores_per_case: dict[str, float] | None = None,
) -> dict:
    """Build a raw result in the shape run_eval produces from Foundry.

    Note this takes VERDICTS, not scores. Foundry decides pass/fail; the
    harness only counts. `scores_per_case` is optional and feeds the scorecard
    display only -- nothing is gated on it, so tests need not supply it.
    """
    verdicts = {**verdicts_per_case, "compliance_safe_answer": compliance}
    cases = [
        {
            "case_id": row["case_id"],
            "failure_tag": row["failure_tag"],
            "response": "…",
            "citations": [],
            "verdicts": dict(verdicts),
            "scores": dict(scores_per_case or {}),
            "verdict": "pass" if all(verdicts.values()) else "fail",
        }
        for row in dataset
    ]
    return {
        "agent_revision": "sha256:test",
        "cases": cases,
        "result_counts": _counts(cases),
    }


def _counts(cases: list[dict]) -> dict:
    """Stand in for Foundry's own tally, derived from the per-case verdicts."""
    failed = sum(1 for c in cases if c["verdict"] == "fail")
    return {
        "total": len(cases),
        "passed": len(cases) - failed,
        "failed": failed,
        "errored": 0,
        "skipped": 0,
    }


def all_pass() -> dict[str, bool]:
    return dict.fromkeys(BUILTINS, True)


def summarise(raw, dataset):
    return run_eval.summarise(raw, CONFIG, "test-agent", dataset, DATASET)


def test_all_metrics_at_threshold_passes(dataset):
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    result = summarise(raw, dataset)
    assert result["verdict"] == "pass"
    assert result["exit_code"] == 0


def test_a_single_breached_metric_fails_the_whole_gate(dataset):
    """No partial credit. One breach is a fail."""
    raw = make_raw(
        {**all_pass(), "groundedness": False},  # the only breach
        compliance=True,
        dataset=dataset,
    )
    result = summarise(raw, dataset)
    assert result["metrics"]["groundedness"]["pass"] is False
    assert result["verdict"] == "fail"
    assert result["exit_code"] == 1


def test_compliance_rubric_requires_a_perfect_pass_rate(dataset):
    """There is no acceptable rate of compliance failure, so 97% must fail."""
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["cases"][0]["verdicts"]["compliance_safe_answer"] = False
    raw["cases"][0]["verdict"] = "fail"
    raw["result_counts"] = _counts(raw["cases"])
    result = summarise(raw, dataset)
    assert result["metrics"]["compliance_safe_answer"]["pass_rate"] < 1.0
    assert result["metrics"]["compliance_safe_answer"]["pass"] is False
    assert result["verdict"] == "fail"


def test_exit_code_tracks_verdict_exactly(dataset):
    for grounded_ok, expected_code in ((True, 0), (False, 1)):
        raw = make_raw(
            {**all_pass(), "groundedness": grounded_ok},
            compliance=True,
            dataset=dataset,
        )
        result = summarise(raw, dataset)
        assert result["exit_code"] == expected_code


def test_results_are_traceable_to_their_inputs(dataset):
    """A scorecard on a projector is only evidence if you can say what produced it."""
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    result = summarise(raw, dataset)
    assert len(result["dataset_sha256"]) == 64
    assert result["agent_revision"] == "sha256:test"
    assert result["judge_model_version"] == "2026-03-17"


def test_failure_tag_rollup_covers_every_staged_mode(dataset):
    raw = make_raw(dict.fromkeys(BUILTINS, False), compliance=False, dataset=dataset)
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


# ─────────────────────────────────────────────────────────────────────────────
# No local scoring. Foundry owns every pass/fail decision; this harness counts
# and reports. A local pass line is a second, private scoring path that can
# disagree with the portal, and when it does there is no way to say which
# number a customer was shown.
# ─────────────────────────────────────────────────────────────────────────────

SOURCE = (Path(ROOT) / "scripts" / "run_eval.py").read_text(encoding="utf-8")


def test_there_is_no_local_fallback_pass_line():
    """A fallback threshold invents a verdict nobody published."""
    assert "CUSTOM_PASS_SCORE" not in SOURCE, (
        "a local pass line is back. If Foundry returns no verdict the run must "
        "exit 2, not fall back to a threshold this harness made up."
    )


def test_the_gate_does_not_compare_scores_to_thresholds_locally():
    """Thresholds are pushed into the testing criteria; Foundry applies them.

    Re-deriving pass/fail from a score here is how the gate and the portal end
    up disagreeing about the same run.
    """
    banned = ("score < thresholds", "score >= threshold", "value >= threshold")
    found = [b for b in banned if b in SOURCE]
    assert not found, f"local threshold comparison reintroduced: {found}"


def test_parse_case_records_a_missing_verdict_as_an_error_not_a_pass():
    """Drive parse_case directly with a result Foundry did not judge.

    An earlier version of this test injected evaluator_errors into an
    already-parsed case, which exercised summarise() and left parse_case's
    handling completely untested -- tampering it to `passed = True` broke
    nothing. Read the real payload shape instead.
    """
    item = {
        "datasource_item": {"case_id": "X", "failure_tag": "t", "query": "q"},
        "sample": {},
        "results": [
            {"name": "groundedness", "score": 5.0, "passed": True},
            # A result with a score but no verdict of any kind.
            {"name": "compliance_safe_answer", "score": 0.95},
        ],
    }
    case = run_eval.parse_case(item, "compliance_safe_answer")

    assert "compliance_safe_answer" not in case["verdicts"], (
        "a criterion Foundry did not judge must not appear as a verdict"
    )
    assert "compliance_safe_answer" in case["evaluator_errors"], (
        "an unjudged criterion must be recorded as an error so the run exits 2"
    )
    assert case["verdicts"]["groundedness"] is True


def test_a_missing_verdict_is_a_harness_failure_not_a_pass(dataset):
    """And that error must take the whole run to exit 2."""
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["cases"][0]["evaluator_errors"] = {
        "compliance_safe_answer": "Foundry returned no pass/fail verdict for this criterion"
    }

    with pytest.raises(SystemExit) as excinfo:
        summarise(raw, dataset)
    assert excinfo.value.code == 2, "a missing verdict must exit 2, never 0 or 1"


def test_the_verdict_comes_from_foundry_not_from_local_counting(dataset):
    """If our tally disagrees with Foundry's, refuse to emit a scorecard.

    Picking a winner between the two would mean the projector and the portal
    can show different outcomes for the same run.
    """
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["result_counts"]["failed"] = 3  # Foundry says three failed; we parsed none
    raw["result_counts"]["passed"] = len(raw["cases"]) - 3

    with pytest.raises(SystemExit) as excinfo:
        summarise(raw, dataset)
    assert excinfo.value.code == 2


def test_absent_result_counts_is_a_harness_failure(dataset, capsys):
    """No counts means Foundry never delivered a verdict to report.

    Assert on the message, not just the exit code. A downstream
    "judged N but parsed M" check also catches an empty counts block, so a
    code-only assertion stayed green even with this guard removed entirely.
    """
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["result_counts"] = {}

    with pytest.raises(SystemExit) as excinfo:
        summarise(raw, dataset)
    assert excinfo.value.code == 2
    assert "no result_counts" in capsys.readouterr().out, (
        "must fail on the absent counts specifically, not incidentally"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Coverage. A rehearsal over 3 of 32 cases once printed a failure-mode table
# listing all 32 staged modes with zero failures, followed by "cleared to
# ship". Every mode looked checked. Twenty-nine had never run.
# ─────────────────────────────────────────────────────────────────────────────


def test_rollup_counts_only_cases_that_were_actually_evaluated(dataset):
    """An unevaluated case must not appear as a clean one."""
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["cases"] = raw["cases"][:3]
    raw["result_counts"] = _counts(raw["cases"])

    result = summarise(raw, dataset)

    counted = sum(b["cases"] for b in result["by_failure_tag"].values())
    assert counted == 3, (
        f"rollup counted {counted} cases but only 3 were evaluated — the table "
        "is describing the dataset file, not the run"
    )


def test_a_partial_run_reports_incomplete_coverage(dataset):
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["cases"] = raw["cases"][:3]
    raw["result_counts"] = _counts(raw["cases"])

    cov = summarise(raw, dataset)["coverage"]
    assert cov["evaluated"] == 3
    assert cov["dataset_cases"] == len(dataset)
    assert cov["complete"] is False
    assert len(cov["unevaluated_case_ids"]) == len(dataset) - 3


def test_a_full_run_reports_complete_coverage(dataset):
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    cov = summarise(raw, dataset)["coverage"]
    assert cov["complete"] is True
    assert cov["unevaluated_case_ids"] == []


def test_a_partial_pass_is_not_described_as_cleared_to_ship(dataset, capsys):
    """The words on the screen are the whole control here."""
    raw = make_raw(all_pass(), compliance=True, dataset=dataset)
    raw["cases"] = raw["cases"][:3]
    raw["result_counts"] = _counts(raw["cases"])
    result = summarise(raw, dataset)

    run_eval.render(result)
    out = capsys.readouterr().out
    assert "cleared to ship" not in out, (
        "a run that evaluated a subset must not claim a ship decision"
    )
    assert "REHEARSAL" in out
