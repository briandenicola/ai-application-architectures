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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import ROOT, ConfigError, console, fail, get_credential, load_config, ok, step, warn
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


def evaluate(config: dict[str, Any], agent_name: str, dataset: list[dict[str, Any]]) -> dict:
    """Submit the dataset to Foundry Evaluations and collect per-case scores.

    Uses the project's evaluation service so that the portal and this script read
    from the same run — the equivalence between the two surfaces is a tested
    property, not a coincidence.
    """
    from azure.ai.projects import AIProjectClient

    project = AIProjectClient(endpoint=config["project"]["endpoint"], credential=get_credential())

    agents = {agent.name: agent.id for agent in project.agents.list_agents()}
    if agent_name not in agents:
        fail(f"Agent '{agent_name}' not found. Run scripts/create_agents.py first.")

    step(f"Evaluating '{agent_name}' over {len(dataset)} cases")
    warn("This calls the judge model once per case per evaluator — expect a few minutes.")

    evaluators = list(config["evaluators"]["builtin"]) + [
        Path(p).stem for p in config["evaluators"]["custom"]
    ]

    run = project.evaluations.create_and_wait(
        agent_id=agents[agent_name],
        data=dataset,
        evaluators=evaluators,
        judge_model=config["models"]["judge"]["deployment"],
    )
    return run.as_dict() if hasattr(run, "as_dict") else dict(run)


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

    metrics: dict[str, Any] = {}
    for name, threshold in thresholds.items():
        scores = [c["scores"].get(name) for c in cases if name in c.get("scores", {})]
        scores = [s for s in scores if s is not None]
        if not scores:
            fail(f"Evaluator '{name}' returned no scores — cannot judge the gate")

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
    args = parser.parse_args()

    config = load_config(args.config)
    dataset_path = ROOT / config["dataset"]
    dataset = load_dataset(dataset_path)

    raw = evaluate(config, args.agent, dataset)
    result = summarise(raw, config, args.agent, dataset, dataset_path)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Never overwrite. Every scorecard shown on stage stays traceable.
    out_path = out_dir / f"{result['agent']}-{result['run_id']}.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    render(result)
    ok(f"Results written to {out_path.relative_to(ROOT)}")
    return int(result["exit_code"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        fail(str(exc))
