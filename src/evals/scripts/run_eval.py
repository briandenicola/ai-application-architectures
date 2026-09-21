#!/usr/bin/env python3
"""Run the evaluation and enforce the quality gate.

Exit codes are load-bearing:

    0  every threshold met          → ship
    1  a threshold was breached     → do not ship
    2  the harness could not run    → fix the environment, verdict unknown

Conflating 1 and 2 is the classic way a quality gate quietly stops protecting
anything, so they are kept strictly separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import (
    ROOT,
    ConfigError,
    console,
    fail,
    load_config,
    ok,
    require_env,
    step,
    warn,
)
from _foundry import FoundryClient, FoundryError
from rich.table import Table

RESULTS_DIR = ROOT / "results"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        fail(f"Dataset not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def render(result: dict[str, Any]) -> None:
    table = Table(title=f"Evaluation — {result['agent']}", title_style="bold")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Score", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_column("Result", justify="center")
    table.add_column("Failed", justify="right")

    for name, metric in result["metrics"].items():
        score = metric.get("mean", metric.get("pass_rate"))
        threshold = result["thresholds"][name]
        passed = metric["pass"]
        table.add_row(
            name,
            f"{score:.2f}",
            f"{threshold:.2f}",
            "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]",
            str(metric["n_failed"]),
        )

    console.print()
    console.print(table)

    rollup = Table(title="Failures by staged failure mode", title_style="bold")
    rollup.add_column("Failure mode", style="cyan")
    rollup.add_column("Cases", justify="right")
    rollup.add_column("Failed", justify="right")
    for tag, counts in result["by_failure_tag"].items():
        failed = counts["failed"]
        style = "bold red" if failed else "green"
        rollup.add_row(tag, str(counts["cases"]), f"[{style}]{failed}[/{style}]")

    console.print()
    console.print(rollup)
    console.print()

    if result["verdict"] == "pass":
        console.print("[bold green]GATE: PASS — cleared to ship[/bold green]")
    else:
        breached = [n for n, m in result["metrics"].items() if not m["pass"]]
        console.print(
            f"[bold red]GATE: FAIL — do not ship[/bold red]  breached: {', '.join(breached)}"
        )
    console.print()


# The third element marks the agentic evaluators. They expect conversation-shaped
# input, not plain strings — pass a string and they silently fall back to a
# degraded parse, still returning a score. A quietly wrong score is worse than an
# error, so the shape is explicit here.
# name -> (foundry evaluator name, data_mapping, scale)
#
# Scales and mappings are NOT guesses: they come from each evaluator's own
# data_schema and init_parameters, fetched from the service. Mirrored here so a
# bad threshold fails a unit test instead of a paid run — see
# tests/test_thresholds.py.
#
# WHY GROUNDEDNESS IS SCORED AGAINST ground_truth, NOT RETRIEVED CONTEXT:
# Foundry exposes the agent's answer and its tool CALLS to evaluators, but not
# the tool OUTPUTS — the retrieved passages never reach the judge. Verified
# against the live service 2026-09-21: mapping `messages` to the trajectory
# fails with "No valid context was provided". So groundedness is given the
# golden set's ground_truth as context, and asks "is this answer supported by
# the authoritative fact for this question?" That is still a real hallucination
# check, and for a compliance audience it is the stronger claim. It is NOT the
# textbook definition of groundedness, and the docs say so plainly.
#
# `retrieval` is deliberately absent: with ground_truth as context it would
# grade the golden set rather than the agent, and score a meaningless 5 every
# time. Retrieval quality is proven instead by the knowledge-base canary in
# scripts/setup_knowledge.py, which runs at provision time. See ADR-0006.
BUILTIN_EVALUATORS = {
    "groundedness": (
        "builtin.groundedness",
        {
            "query": "{{item.query}}",
            "context": "{{item.ground_truth}}",
            "response": "{{sample.output_text}}",
        },
        (1, 5),
    ),
    "relevance": (
        "builtin.relevance",
        {"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        (1, 5),
    ),
    "intent_resolution": (
        "builtin.intent_resolution",
        {"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        (1, 5),
    ),
    # Boolean, NOT 1-5. The catalog contradicts itself here: this evaluator's
    # init_parameters advertise a threshold range of 1-5, but its declared metric
    # type is `boolean` and it emits 0 or 1. A 4.0 threshold is therefore
    # unreachable and fails every case while the judge's own reason reads as a
    # pass. verify_scales() checks this against the live catalog on every run.
    "task_adherence": (
        "builtin.task_adherence",
        {"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        (0, 1),
    ),
}

CUSTOM_METRIC = "compliance_safe_answer"
CUSTOM_SCALE = (0.0, 1.0)

# Fallback pass line, used only if Foundry does not report its own verdict.
# Mirrors pass_threshold in evaluators/compliance_safe_answer.yaml.
CUSTOM_PASS_SCORE = 0.9

TERMINAL_STATES = {"completed", "failed", "canceled"}


def check_thresholds(config: dict[str, Any]) -> list[str]:
    """Reject thresholds that sit outside their metric's scale."""
    problems = []
    for name in config["evaluators"]["builtin"]:
        if name not in BUILTIN_EVALUATORS:
            problems.append(f"'{name}' is not a known built-in evaluator")
            continue
        low, high = BUILTIN_EVALUATORS[name][2]
        threshold = config["thresholds"][name]
        if not low <= threshold <= high:
            problems.append(
                f"'{name}' threshold {threshold} is outside its {low}-{high} scale — "
                "the metric could never pass"
            )
    low, high = CUSTOM_SCALE
    custom = config["thresholds"][CUSTOM_METRIC]
    if not low <= custom <= high:
        problems.append(f"'{CUSTOM_METRIC}' threshold {custom} is outside its {low}-{high} scale")
    return problems


def verify_scales(client: FoundryClient, config: dict[str, Any]) -> None:
    """Check our mirrored scales against the catalog before spending anything.

    Evaluators are versioned and their scales have already changed underneath
    this demo once. A drifted scale does not error — it silently fails or passes
    every case — so it is worth one GET to catch.
    """
    catalog = {
        e["name"]: e for e in client.paged("/evaluators", params={"type": "builtin"}, preview=True)
    }
    for name in config["evaluators"]["builtin"]:
        evaluator_name, _mapping, (low, high) = BUILTIN_EVALUATORS[name]
        entry = catalog.get(evaluator_name)
        if not entry:
            warn(f"'{evaluator_name}' is not in the evaluator catalog.")
            continue
        metrics = (entry.get("definition") or {}).get("metrics") or {}
        declared = next(iter(metrics.values()), {})
        if declared.get("type") == "boolean":
            if (low, high) != (0, 1):
                fail(
                    f"'{name}' is a boolean metric in the catalog but is configured "
                    f"on a {low}-{high} scale. Every case would fail."
                )
            continue
        catalog_low = declared.get("min_value")
        catalog_high = declared.get("max_value")
        if catalog_low is not None and (catalog_low, catalog_high) != (low, high):
            fail(
                f"'{name}' scale drifted: catalog says {catalog_low}-{catalog_high}, "
                f"this run assumes {low}-{high}. Re-check thresholds before running."
            )


def build_testing_criteria(config: dict[str, Any], judge_model: str) -> list[dict[str, Any]]:
    """Describe to Foundry how each case should be scored."""
    criteria: list[dict[str, Any]] = []
    for name in config["evaluators"]["builtin"]:
        evaluator_name, mapping, _scale = BUILTIN_EVALUATORS[name]
        criteria.append(
            {
                "type": "azure_ai_evaluator",
                "name": name,
                "evaluator_name": evaluator_name,
                # Built-ins take `deployment_name`; the custom rubric takes
                # `model`. Swapping them is a 400 with an unhelpful message.
                "initialization_parameters": {
                    "deployment_name": judge_model,
                    "threshold": config["thresholds"][name],
                },
                "data_mapping": mapping,
            }
        )

    criteria.append(
        {
            "type": "azure_ai_evaluator",
            "name": CUSTOM_METRIC,
            "evaluator_name": config["evaluators"]["custom_name"],
            "initialization_parameters": {"model": judge_model},
            # Same limitation as the built-ins: no tool outputs are exposed, so
            # the rubric judges the answer against the authoritative fact.
            "data_mapping": {
                "query": "{{item.query}}",
                "response": "{{sample.output_text}}",
            },
        }
    )
    return criteria


def poll_run(
    client: FoundryClient, eval_id: str, run_id: str, timeout_seconds: int = 3600
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_status = ""
    while time.time() < deadline:
        run = client.get(f"/openai/v1/evals/{eval_id}/runs/{run_id}")
        status = run.get("status", "")
        if status != last_status:
            console.print(f"  [dim]status: {status}[/dim]")
            last_status = status
        if status in TERMINAL_STATES:
            return run
        time.sleep(15)
    fail(f"Evaluation run did not finish within {timeout_seconds}s. Run id: {run_id}")
    return {}


def fetch_output_items(client: FoundryClient, eval_id: str, run_id: str) -> list[dict[str, Any]]:
    """Page through per-case results.

    Paging is not optional: the default page size is far smaller than the
    dataset, so a single GET would quietly gate on a subset.
    """
    items: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {"limit": 100}
        if after:
            params["after"] = after
        page = client.get(f"/openai/v1/evals/{eval_id}/runs/{run_id}/output_items", params=params)
        batch = page.get("data", page.get("value", []))
        items.extend(batch)
        if not page.get("has_more") or not batch:
            return items
        after = batch[-1].get("id")


def result_passed(entry: dict[str, Any]) -> bool | None:
    """Foundry's own verdict for a criterion, when it reports one."""
    for key in ("passed", "pass"):
        if isinstance(entry.get(key), bool):
            return entry[key]
    outcome = entry.get("result") or entry.get("status")
    if isinstance(outcome, str) and outcome.lower() in {"pass", "passed", "fail", "failed"}:
        return outcome.lower().startswith("pass")
    return None


def score_from_result(entry: dict[str, Any]) -> float | None:
    for key in ("score", "value", "result"):
        value = entry.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
    return None


def response_text(sample: dict[str, Any]) -> str:
    """Pull the agent's final answer out of the sample transcript.

    `sample.output` is a message LIST, not an `output_text` string. The last
    assistant turn holds the answer; earlier ones hold tool calls, and their
    content is a JSON blob rather than prose. Reading the wrong key silently
    stores an empty response on every case, which strips the demo of the one
    artifact a client most wants to see: what the agent actually said.
    """
    direct = sample.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output = sample.get("output")
    if isinstance(output, str):
        return output.strip()
    if not isinstance(output, list):
        return ""

    for message in reversed(output):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        # Tool-call turns serialise a JSON array into content. Those are not the
        # answer, and rendering one would be actively misleading.
        stripped = content.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return stripped
            texts = [
                part.get("text")
                for part in parsed
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            ]
            if texts:
                return "\n".join(t.strip() for t in texts if t.strip())
            continue
        return stripped
    return ""


def parse_case(item: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
    source = item.get("datasource_item") or {}
    sample = item.get("sample") or {}

    scores: dict[str, Any] = {}
    reasons: dict[str, str] = {}
    errors: dict[str, str] = {}
    for entry in item.get("results", []) or []:
        name = entry.get("name") or entry.get("testing_criteria")
        if not name:
            continue
        if entry.get("status") == "error":
            # An evaluator that errored produced NO verdict. Recording it is what
            # keeps summarise() from averaging over the survivors and reporting a
            # clean pass rate for a metric that never ran. See the pii_leak case.
            detail = ((entry.get("sample") or {}).get("error") or {}).get("message", "")
            errors[name] = detail or "evaluator reported status=error"
            continue
        score = score_from_result(entry)
        passed = result_passed(entry)
        if name == CUSTOM_METRIC:
            # The rubric returns a continuous 0-1 score, but the pass line lives
            # in the evaluator definition in Foundry. Defer to the service's
            # verdict so the portal and this gate can never disagree.
            if passed is None and score is None:
                continue
            scores[name] = passed if passed is not None else score >= CUSTOM_PASS_SCORE
        elif score is not None:
            scores[name] = score
        else:
            continue
        reason = entry.get("reason") or (entry.get("metadata") or {}).get("reason")
        if reason:
            reasons[name] = reason

    failed = [
        name for name, score in scores.items() if name in thresholds and score < thresholds[name]
    ]

    return {
        "case_id": source.get("case_id"),
        "failure_tag": source.get("failure_tag"),
        "query": source.get("query"),
        "response": response_text(sample),
        "citations": [],
        "scores": scores,
        "evaluator_errors": errors,
        "compliance_reason": reasons.get(CUSTOM_METRIC, ""),
        "reasons": reasons,
        "verdict": "fail" if failed else "pass",
        "failed_metrics": failed,
    }


def evaluate(
    config: dict[str, Any],
    agent_name: str,
    dataset: list[dict[str, Any]],
    dataset_name: str,
    dataset_version: str,
) -> dict[str, Any]:
    """Ask Foundry to evaluate the agent, then gate on what it reports.

    Nothing is scored locally. Foundry calls the published prompt agent itself
    (`target.type = azure_ai_agent`), runs every evaluator server-side, and
    stores the run — so the scorecard on the Evaluations tab and the scorecard in
    this terminal are the same artifact, not two things that might disagree.
    """
    problems = check_thresholds(config)
    if problems:
        fail("Threshold configuration is unusable:\n  - " + "\n  - ".join(problems))

    account = require_env("AZURE_AI_FOUNDRY_NAME")["AZURE_AI_FOUNDRY_NAME"]
    project_name = config["project"]["endpoint"].rstrip("/").rsplit("/", 1)[-1]
    dataset_id = (
        f"azureai://accounts/{account}/projects/{project_name}"
        f"/data/{dataset_name}/versions/{dataset_version}"
    )
    judge_model = config["models"]["judge"]["deployment"]
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    with FoundryClient(config["project"]["endpoint"]) as client:
        verify_scales(client, config)
        version = agent_version(client, agent_name)
        step(f"Creating evaluation for '{agent_name}' v{version}")
        try:
            evaluation = client.post(
                "/openai/v1/evals",
                json_body={
                    "name": f"{agent_name} — {run_id}",
                    "data_source_config": {
                        "type": "custom",
                        "item_schema": {
                            "type": "object",
                            "properties": {
                                "case_id": {"type": "string"},
                                "failure_tag": {"type": "string"},
                                "query": {"type": "string"},
                                "ground_truth": {"type": "string"},
                            },
                            "required": ["query"],
                        },
                        "include_sample_schema": True,
                    },
                    "testing_criteria": build_testing_criteria(config, judge_model),
                    "metadata": {"agent": agent_name, "demo": "meridian-foundry-evals"},
                },
            )
        except FoundryError as exc:
            fail(f"Could not create the evaluation:\n{exc}")

        eval_id = evaluation["id"]
        ok(f"Evaluation created — {eval_id}")

        step(f"Running against agent '{agent_name}' v{version} over {len(dataset)} cases")
        warn("Foundry calls the agent and every evaluator. This costs tokens.")
        try:
            run = client.post(
                f"/openai/v1/evals/{eval_id}/runs",
                json_body={
                    "name": f"{agent_name}-{run_id}",
                    "data_source": {
                        "type": "azure_ai_target_completions",
                        "source": {"type": "file_id", "id": dataset_id},
                        "input_messages": {
                            "type": "template",
                            "template": [
                                {
                                    "type": "message",
                                    "role": "user",
                                    "content": {
                                        "type": "input_text",
                                        "text": "{{item.query}}",
                                    },
                                }
                            ],
                        },
                        "target": {
                            "type": "azure_ai_agent",
                            "name": agent_name,
                            "version": version,
                        },
                    },
                },
            )
        except FoundryError as exc:
            fail(f"Could not start the evaluation run:\n{exc}")

        foundry_run_id = run["id"]
        report_url = run.get("report_url", "")
        if report_url:
            ok(f"Live in the portal — {report_url}")

        final = poll_run(client, eval_id, foundry_run_id)
        if final.get("status") != "completed":
            fail(
                f"Run ended with status '{final.get('status')}'. "
                f"See {final.get('report_url') or report_url}"
            )

        counts = final.get("result_counts", {})
        if counts.get("errored"):
            warn(f"{counts['errored']} case(s) errored server-side — scores will be incomplete.")

        items = fetch_output_items(client, eval_id, foundry_run_id)

    if not items:
        fail("Foundry returned no per-case results — nothing to gate on.")

    cases = [parse_case(item, config["thresholds"]) for item in items]
    return {
        "cases": cases,
        "agent_version": version,
        "agent_revision": agent_revision(agent_name),
        "studio_url": final.get("report_url") or report_url,
        "eval_id": eval_id,
        "run_id": foundry_run_id,
    }


def agent_version(client: FoundryClient, agent_name: str) -> str:
    """Resolve the newest published version.

    Pinning "1" evaluates whatever was published first, which silently scores a
    stale agent after any republish — the failure mode is a scorecard that looks
    fine and describes the wrong thing.
    """
    versions = client.paged(f"/agents/{agent_name}/versions")
    if not versions:
        fail(f"Agent '{agent_name}' has no published versions. Run scripts/create_agents.py.")
    newest = max(versions, key=lambda v: int(v["version"]))
    return str(newest["version"])


def agent_revision(agent_name: str) -> str:
    state_file = ROOT / ".azure" / "agents.json"
    if not state_file.exists():
        return "unknown"
    return (
        json.loads(state_file.read_text(encoding="utf-8"))
        .get(agent_name, {})
        .get("revision", "unknown")
    )


def summarise(
    raw: dict[str, Any],
    config: dict[str, Any],
    agent_name: str,
    dataset: list[dict[str, Any]],
    dataset_path: Path,
) -> dict[str, Any]:
    thresholds: dict[str, float] = config["thresholds"]
    cases: list[dict[str, Any]] = raw.get("cases", [])
    by_case_id = {c["case_id"]: c for c in cases}

    # An evaluator that errored returns no verdict. Averaging over the survivors
    # yields a confident score for a metric that did not run on every case --
    # observed live: the compliance rubric errored on 2 of 3 pii_leak cases and
    # the scorecard reported that mode as 0 failures. A gate that cannot tell
    # "passed" from "never ran" protects nothing, so this is a HARNESS failure
    # (exit 2), deliberately distinct from a quality failure (exit 1).
    errored = [
        (c["case_id"], name, msg)
        for c in cases
        for name, msg in (c.get("evaluator_errors") or {}).items()
    ]
    if errored:
        lines = "\n".join(f"  {cid}  {name}: {msg}" for cid, name, msg in errored[:10])
        more = f"\n  …and {len(errored) - 10} more" if len(errored) > 10 else ""
        fail(
            f"{len(errored)} evaluator result(s) errored server-side — the gate "
            f"cannot be judged on partial scoring:\n{lines}{more}"
        )

    metrics: dict[str, Any] = {}
    for name, threshold in thresholds.items():
        scores = [c["scores"].get(name) for c in cases if name in c.get("scores", {})]
        scores = [s for s in scores if s is not None]
        if not scores:
            fail(f"Evaluator '{name}' returned no scores — cannot judge the gate")
        if len(scores) != len(cases):
            fail(
                f"Evaluator '{name}' scored only {len(scores)} of {len(cases)} cases. "
                "A metric that skipped cases cannot gate a release."
            )

        if name == "compliance_safe_answer":
            value = sum(1 for s in scores if s) / len(scores)
            n_failed = sum(1 for s in scores if not s)
            metrics[name] = {
                "pass_rate": value,
                "pass": value >= threshold,
                "n_failed": n_failed,
            }
        else:
            value = sum(scores) / len(scores)
            n_failed = sum(1 for s in scores if s < threshold)
            metrics[name] = {"mean": value, "pass": value >= threshold, "n_failed": n_failed}

    by_tag: dict[str, dict[str, int]] = {}
    for row in dataset:
        tag = row["failure_tag"]
        bucket = by_tag.setdefault(tag, {"cases": 0, "failed": 0})
        bucket["cases"] += 1
        case = by_case_id.get(row["case_id"])
        if case and case.get("verdict") == "fail":
            bucket["failed"] += 1

    verdict = "pass" if all(m["pass"] for m in metrics.values()) else "fail"

    return {
        "run_id": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"),
        "foundry_eval_id": raw.get("eval_id", ""),
        "foundry_run_id": raw.get("run_id", ""),
        "agent": agent_name,
        "agent_revision": raw.get("agent_revision", "unknown"),
        "dataset": dataset_path.name,
        "dataset_sha256": sha256_file(dataset_path),
        "judge_model": config["models"]["judge"]["deployment"],
        "judge_model_version": config["models"]["judge"]["version"],
        "thresholds": thresholds,
        "metrics": metrics,
        "by_failure_tag": by_tag,
        "cases": cases,
        "verdict": verdict,
        "exit_code": 0 if verdict == "pass" else 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Meridian evaluation quality gate.")
    parser.add_argument("--agent", required=True, help="Agent name, e.g. meridian-advisor-v1")
    parser.add_argument("--config", default="evals.config.yaml")
    parser.add_argument("--out", default=str(RESULTS_DIR))
    parser.add_argument(
        "--dataset-name",
        help="Foundry dataset to evaluate against. Defaults to evals.config.yaml. "
        "Point at a smaller seeded dataset to rehearse cheaply.",
    )
    parser.add_argument(
        "--dataset-version",
        help="Version of the Foundry dataset. Defaults to evals.config.yaml.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Trim the local case list used for the by-failure-mode table. Foundry "
        "evaluates whatever the named dataset contains, so use --dataset-name to "
        "actually shrink a run. Marked as partial and never a gate result.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    dataset_path = ROOT / config["dataset"]["path"]
    dataset = load_dataset(dataset_path)
    if args.limit:
        dataset = dataset[: args.limit]
        warn(f"--limit {args.limit}: this is a smoke run, NOT a gate result.")

    dataset_name = args.dataset_name or config["dataset"]["name"]
    dataset_version = args.dataset_version or str(config["dataset"]["version"])
    raw = evaluate(config, args.agent, dataset, dataset_name, dataset_version)
    result = summarise(raw, config, args.agent, dataset, dataset_path)
    if args.limit:
        result["partial_run"] = True
        result["cases_evaluated"] = len(dataset)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Never overwrite. Every scorecard shown on stage stays traceable.
    suffix = "-partial" if args.limit else ""
    out_path = out_dir / f"{result['agent']}-{result['run_id']}{suffix}.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    render(result)
    ok(f"Results written to {out_path.relative_to(ROOT)}")
    return int(result["exit_code"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        fail(str(exc))
