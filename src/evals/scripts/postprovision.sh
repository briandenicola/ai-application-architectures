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

python scripts/index_corpus.py
python scripts/setup_knowledge.py
python scripts/create_agents.py

echo
echo "✓ Demo environment ready."
echo "  Portal:  ${AZURE_AI_PROJECT_ENDPOINT:-<run: azd env get-values>}"
echo
echo "  Next:"
echo "    python scripts/run_eval.py --agent meridian-advisor-v1   # expect exit 1"
echo "    python scripts/run_eval.py --agent meridian-advisor-v2   # expect exit 0"
echo
