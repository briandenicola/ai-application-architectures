"""Ask an agent a list of questions and record exactly what it said.

This is a probe, not an evaluation. Nothing here scores anything — scoring
happens in Foundry, against a published rubric, on a registered dataset. The
only job of this script is to find out what a naive agent *actually* does
before anyone writes an expected answer.

That distinction has been expensive to learn. The FinOps golden set was drafted
against assumed behaviour, three of its six traps never fired, and it had to be
cut from 32 cases to 26 after the fact. A trap that does not fire proves
nothing about the guard that would have caught it, and a golden case built on
one is worse than no case at all: it passes, and it looks like evidence.

    python scripts/probe_agent.py --agent meridian-people-v1 \\
        --questions probes/hr-probe.json --out /tmp/v1-hr-probe.json

Output is a JSON array of the input records with an `answer` field added, so a
v1 run and a v2 run can be diffed directly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _common import console, fail, load_config, step  # noqa: E402


def build_project(endpoint: str):
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    return AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())


def ask(project, agent: str, model: str, question: str, timeout: float = 900.0) -> str:
    """One question, one answer.

    Retries only two things, both infrastructure rather than content: Search
    RBAC still propagating, and a 429 from the shared model deployment. All
    three demo tracks share one gpt-5.5 deployment and a probe of any size will
    trip its rate limit partway through — observed on HR round 2, which lost
    four of nine answers and needed a second pass.

    A retry on either is a retry on the *transport*. The answer itself is never
    re-asked because it disagreed with expectations; a probe that quietly
    re-rolls until it likes the result is measuring patience, not behaviour.
    """
    client = project.get_openai_client(agent_name=agent)
    deadline = time.monotonic() + timeout
    backoff = 30.0
    while True:
        try:
            response = client.responses.create(input=question, model=model)
            return (getattr(response, "output_text", "") or "").strip()
        except Exception as exc:  # noqa: BLE001 - the answer is the artefact
            text = str(exc)
            rate_limited = "429" in text or "rate_limit_exceeded" in text
            rbac = "Access denied" in text
            if (rate_limited or rbac) and time.monotonic() < deadline:
                wait = backoff if rate_limited else 30.0
                reason = "model quota" if rate_limited else "search RBAC"
                console.print(f"  [dim]{reason}: waiting {wait:.0f}s…[/dim]")
                time.sleep(wait)
                if rate_limited:
                    backoff = min(backoff * 2, 240.0)
                continue
            return f"<<ERROR: {exc}>>"


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe an agent with a list of questions.")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", type=int, nargs="*", help="probe only these question numbers")
    args = parser.parse_args()

    if not args.questions.exists():
        fail(f"no such questions file: {args.questions}")

    with args.questions.open(encoding="utf-8") as handle:
        questions = json.load(handle)
    if args.only:
        questions = [q for q in questions if q.get("n") in set(args.only)]
    if not questions:
        fail("no questions selected")

    config = load_config()
    endpoint = config["project"]["endpoint"]
    model = os.environ.get("AZURE_AI_AGENT_MODEL_DEPLOYMENT")
    if not model:
        fail("AZURE_AI_AGENT_MODEL_DEPLOYMENT is not set")

    project = build_project(endpoint)
    results = []
    for record in questions:
        step(f"[{record.get('n')}] {record.get('trap', '?')}")
        console.print(f"  [dim]{record['question']}[/dim]")
        answer = ask(project, args.agent, model, record["question"])
        console.print(f"  {answer[:300]}{'…' if len(answer) > 300 else ''}\n")
        results.append({**record, "agent": args.agent, "answer": answer})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    console.print(f"✓ {len(results)} answers written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
