#!/usr/bin/env python3
"""Publish the custom rubric evaluator into the Foundry evaluator catalog.

Run by azd's post-provision hook. After this, `Compliance-Safe Answer` is
selectable in the portal's Create-evaluation flow alongside Microsoft's
built-ins — which is the point: the compliance rule the client cares about
becomes a platform object, not a script on someone's laptop.

Idempotent: creating a new version of an existing evaluator is the intended
update path, so re-running is safe and leaves a version history.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ROOT,
    console,
    fail,
    load_config,
    ok,
    select_corpus,
    step,
)
from _foundry import FoundryClient, FoundryError  # noqa: E402


def build_payload(spec: dict) -> dict:
    definition = spec["definition"]
    dimensions = [
        {
            "id": dimension["id"],
            "description": " ".join(dimension["description"].split()),
            "weight": dimension["weight"],
            "always_applicable": dimension.get("always_applicable", False),
        }
        for dimension in definition["dimensions"]
    ]
    # Flat body. The spec's nested {"type": "custom", "evaluator": {...}} form is
    # rejected with "The Definition field is required." — verified against the
    # live service 2026-09-21.
    return {
        "display_name": spec["display_name"],
        "description": " ".join(spec["description"].split()),
        "evaluator_type": "custom",
        "categories": spec.get("categories", ["quality"]),
        "definition": {
            "type": "rubric",
            "dimensions": dimensions,
            "pass_threshold": definition["pass_threshold"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the custom rubric evaluator.")
    parser.add_argument(
        "--corpus",
        choices=("meridian", "finops", "hr"),
        default="meridian",
        help="Which track's rubric to publish. Swaps in the _finops config blocks.",
    )
    args = parser.parse_args()

    config = select_corpus(load_config(), args.corpus)
    spec_path = ROOT / config["evaluators"]["custom"][0]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    name = spec["name"]
    payload = build_payload(spec)

    console.print()
    console.rule("[bold]Foundry evaluator catalog")

    dimension_count = len(payload["definition"]["dimensions"])
    step(f"Publishing rubric evaluator '{name}' ({dimension_count} dimensions)")
    with FoundryClient(config["project"]["endpoint"]) as client:
        try:
            created = client.post(f"/evaluators/{name}/versions", json_body=payload, preview=True)
        except FoundryError as exc:
            fail(f"Could not publish evaluator '{name}':\n{exc}")

    version = created.get("version", "?")
    ok(f"Published '{name}' version {version}")
    console.print(f"  [dim]{created.get('id', '')}[/dim]")
    ok("Selectable in the portal under Evaluations → Evaluator catalog")
    return 0


if __name__ == "__main__":
    sys.exit(main())
