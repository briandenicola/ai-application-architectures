"""The two azd post-provision hooks must do the same thing.

They are one contract expressed in two shells. When they drift, the result is
an environment that works on the presenter's laptop and is quietly missing a
step on a colleague's — and the missing step is not discovered until the demo
is already running.

This is not hypothetical. Before the FinOps track was added, the PowerShell
hook had silently lost both `seed_evaluator.py` and `seed_dataset.py`. A
Windows `azd up` produced a project with agents but no dataset and no
evaluator, so the portal offered nothing to evaluate against. Nothing failed;
there was simply nothing there.
"""

from __future__ import annotations

import re

from conftest import ROOT

SH = ROOT / "scripts" / "postprovision.sh"
PS1 = ROOT / "scripts" / "postprovision.ps1"

SCRIPT = re.compile(r"scripts/(\w+\.py)")


def sh_steps() -> list[tuple[str, str]]:
    steps = []
    for line in SH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        # Only real invocations. `echo` lines advertise commands to the user
        # and are not steps the hook performs.
        if not line.startswith("python scripts/"):
            continue
        match = SCRIPT.search(line)
        assert match
        corpus = "finops" if "--corpus finops" in line else "meridian"
        steps.append((match.group(1), corpus))
    return steps


def ps1_steps() -> list[tuple[str, str]]:
    text = PS1.read_text(encoding="utf-8")
    block = text.split("$steps = @(", 1)[1].split("\n)", 1)[0]
    steps = []
    for line in block.splitlines():
        match = SCRIPT.search(line)
        if not match:
            continue
        corpus = "finops" if "finops" in line else "meridian"
        steps.append((match.group(1), corpus))
    return steps


def test_both_hooks_exist():
    assert SH.exists() and PS1.exists()


def test_the_hooks_run_the_same_steps_in_the_same_order():
    assert sh_steps() == ps1_steps(), (
        "postprovision.sh and postprovision.ps1 have drifted. They are one "
        "contract in two shells — a step in one and not the other produces an "
        "environment that is broken only on the other platform."
    )


def test_both_tracks_are_provisioned():
    """A track that is only ever set up by hand is a track that is missing on
    the one morning nobody has time to notice, and its absence looks exactly
    like a broken deployment."""
    steps = sh_steps()
    corpora = {corpus for _, corpus in steps}
    assert corpora == {"meridian", "finops"}, (
        f"post-provision covers only {corpora}. Both demo tracks must come up "
        "with `azd up` or neither should."
    )


def test_each_track_indexes_publishes_and_seeds():
    """Every track needs all four: without the dataset and the evaluator, the
    portal has nothing to run an evaluation against."""
    steps = sh_steps()
    for corpus in ("meridian", "finops"):
        scripts = {script for script, track in steps if track == corpus}
        for required in (
            "index_corpus.py",
            "create_agents.py",
            "seed_evaluator.py",
            "seed_dataset.py",
        ):
            assert required in scripts, f"{corpus} track never runs {required}"


def test_the_shell_hook_aborts_on_failure():
    """Without `set -e` a failed step prints an error and the hook exits 0, so
    `azd up` reports success over a half-configured environment."""
    assert re.search(r"^set -eu?", SH.read_text(encoding="utf-8"), re.M)


def test_the_powershell_hook_aborts_on_failure():
    text = PS1.read_text(encoding="utf-8")
    assert "$ErrorActionPreference = 'Stop'" in text
    assert "LASTEXITCODE" in text, (
        "native executables do not trip ErrorActionPreference; the exit code "
        "must be checked explicitly or a failed step passes silently"
    )
