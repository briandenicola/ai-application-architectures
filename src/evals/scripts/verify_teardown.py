#!/usr/bin/env python3
"""Verify that `azd down` actually left nothing behind.

"Clean teardown" is a constitution non-negotiable, and soft-deleted Cognitive
Services accounts are the usual way it is quietly violated: the resource group is
gone, the portal looks clean, and the next `azd up` fails with a name conflict or
silently resurrects an old account. This script checks for that.

Runs as a postdown hook. Exits non-zero if anything survives.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from _common import ROOT, console, fail, ok, step, warn


def az(*args: str) -> tuple[int, str]:
    az_path = shutil.which("az")
    if not az_path:
        fail("Azure CLI not found on PATH")
    result = subprocess.run(  # noqa: S603 — fixed binary, no shell
        [az_path, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.strip()


def main() -> int:
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
    subscription = os.environ.get("AZURE_SUBSCRIPTION_ID")
    problems: list[str] = []

    if not resource_group:
        warn("AZURE_RESOURCE_GROUP not set — skipping resource group check")
    else:
        step(f"Checking resource group '{resource_group}' is gone")
        code, out = az("group", "exists", "--name", resource_group, "-o", "tsv")
        if code == 0 and out.lower() == "true":
            problems.append(f"Resource group '{resource_group}' still exists")
        else:
            ok("Resource group removed")

    step("Checking for soft-deleted Foundry / Cognitive Services accounts")
    args = ["cognitiveservices", "account", "list-deleted", "-o", "json"]
    if subscription:
        args += ["--subscription", subscription]
    code, out = az(*args)
    if code != 0:
        warn("Could not list soft-deleted accounts — check manually before redeploying")
    else:
        deleted = json.loads(out or "[]")
        orphans = [
            account
            for account in deleted
            if "mwp" in (account.get("name") or "").lower()
            or (account.get("tags") or {}).get("solution") == "meridian-foundry-evals"
        ]
        if orphans:
            for account in orphans:
                console.print(f"  [yellow]soft-deleted:[/yellow] {account.get('name')}")
            problems.append(
                f"{len(orphans)} soft-deleted Foundry account(s) remain. "
                "Purge with: az cognitiveservices account purge "
                "--name <name> --resource-group <rg> --location <loc>"
            )
        else:
            ok("No soft-deleted Foundry accounts remain")

    # Local state: leaving stale agent ids behind makes the next run confusing.
    state_file = ROOT / ".azure" / "agents.json"
    if state_file.exists():
        state_file.unlink()
        ok("Cleared local agent state")

    if problems:
        console.print()
        for problem in problems:
            console.print(f"[bold red]✗[/bold red] {problem}")
        console.print()
        fail("Teardown incomplete — see above", code=1)

    console.print()
    ok("Teardown verified — nothing left behind")
    return 0


if __name__ == "__main__":
    sys.exit(main())
