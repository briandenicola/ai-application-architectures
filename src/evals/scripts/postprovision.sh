#!/bin/sh
# azd postprovision hook. Any failure aborts `azd up` — a half-configured demo
# environment is worse than no environment, because it fails on stage instead of
# in the terminal.
set -eu

cd "$(dirname "$0")/.."

echo "──────────────────────────────────────────────────────────────"
echo " Meridian Foundry Evals — post-provision configuration"
echo "──────────────────────────────────────────────────────────────"

PY="${PYTHON:-python3}"

if [ ! -d .venv ]; then
  echo "→ Creating virtual environment"
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate

echo "→ Installing dependencies"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -e .

echo "→ Waiting 60s for RBAC propagation"
# Role assignments made during provisioning are not always effective immediately.
# Without this the first data-plane call after `azd up` intermittently 403s.
sleep 60

# ── Track 1: the advisor demo ────────────────────────────────────────────────
echo "→ Advisor track"
python scripts/index_corpus.py
python scripts/setup_knowledge.py
python scripts/create_agents.py

# Seed the Foundry-side evaluation assets. The evaluator catalog entry and the
# golden dataset must exist before anyone can create a run in the portal, and
# the demo is run FROM the portal -- azd seeds, the presenter evaluates.
python scripts/seed_evaluator.py
python scripts/seed_dataset.py

# ── Track 2: the AI Platform FinOps demo ─────────────────────────────────────
# Provisioned unconditionally, and deliberately so. A track that is only set up
# by hand is a track that is missing on the one morning nobody has time to
# notice -- and its absence looks identical to a broken deployment. Both demos
# either come up together or `azd up` fails.
echo "→ FinOps track"
python scripts/index_corpus.py  --corpus finops
python scripts/create_agents.py --corpus finops
python scripts/seed_evaluator.py --corpus finops
python scripts/seed_dataset.py   --corpus finops

echo
echo "✓ Demo environment ready."
echo "  Portal:  ${AZURE_AI_PROJECT_ENDPOINT:-<run: azd env get-values>}"
echo
echo "  Next — either run a gate from the terminal:"
echo "    python scripts/run_eval.py --agent meridian-advisor-v1   # expect exit 1"
echo "    python scripts/run_eval.py --agent meridian-advisor-v2   # expect exit 0"
echo "    python scripts/run_eval.py --corpus finops --agent meridian-finops-v1  # expect exit 1"
echo "    python scripts/run_eval.py --corpus finops --agent meridian-finops-v2  # expect exit 0"
echo
echo "  …or create the run in the portal against the seeded datasets and"
echo "  evaluators. Both paths execute inside Foundry and produce the same run."
echo "  Portal walkthrough: docs/finops-run-of-show.md"
echo
