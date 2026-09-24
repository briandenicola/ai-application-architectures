"""Does the rewritten `citation_discipline` actually fire?

T23 is the reason this exists. A dimension can be well-formed, published and
weighted, and still score nothing — that is exactly what the citation columns
did for two commits. A guard proving the prose is correct is not evidence the
judge acts on it, so the rewritten dimension gets checked against the service
before anyone calls it a control.

The rewrite made `citation_discipline` self-contained: it names the superseded
document in its own text and asks a question answerable from the response
alone — did the answer name the document it rests on?

The experiment
--------------
Three responses to the same 2026 question, whose correct answer is $40.00 per
1M from `meridian-model-rate-card-2026-01`.

  cites-current        names the current card, correct figure    -> high
  unsourced            CORRECT figure, names no document         -> citation_discipline 1
  superseded-as-current  presents the 2025-10 card as current    -> citation_discipline 1

`unsourced` is the load-bearing arm. Its figure is right, so every other
dimension should be content; only the attribution is missing. If it scores the
same as `cites-current`, the rewrite failed and the dimension is still inert.

`superseded-as-current` will also trip `rate_card_in_effect`, so it cannot
isolate the dimension on its own — it is here to confirm the superseded
document is recognised by name.

No agent is called: 3 judge calls on gpt-4.1-mini, no gpt-5.5 quota.

Run:  .venv/bin/python probes/citation_discipline_probe.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _common import load_config, select_corpus  # noqa: E402
from _foundry import FoundryClient, FoundryError  # noqa: E402

QUERY = "What does gpt-5.5 output cost per 1M under the current rate card?"

ITEMS = [
    {
        "case_id": "cites-current",
        "query": QUERY,
        "response": (
            "Per meridian-model-rate-card-2026-01, effective 2026-01-01, "
            "gpt-5.5 output is priced at $40.00 per 1M tokens."
        ),
    },
    {
        "case_id": "unsourced",
        "query": QUERY,
        # The figure is CORRECT. Only the attribution is missing, which is the
        # single thing the rewritten dimension is supposed to notice.
        "response": "gpt-5.5 output is priced at $40.00 per 1M tokens.",
    },
    {
        "case_id": "superseded-as-current",
        "query": QUERY,
        "response": (
            "Per the current rate card, meridian-model-rate-card-2025-10, "
            "gpt-5.5 output is priced at $50.00 per 1M tokens."
        ),
    },
]


def main() -> int:
    config = select_corpus(load_config(), "finops")
    judge_model = config["models"]["judge"]["deployment"]
    rubric = config["evaluators"]["custom_name"]

    with FoundryClient(config["project"]["endpoint"]) as client:
        versions = client.paged(f"/evaluators/{rubric}/versions", preview=True)
        pinned = str(max(int(v["version"]) for v in versions))
        print(f"judge : {judge_model}")
        print(f"rubric: {rubric} v{pinned}\n")

        evaluation = client.post(
            "/openai/v1/evals",
            json_body={
                "name": "PROBE citation_discipline fires — delete me",
                "data_source_config": {
                    "type": "custom",
                    "item_schema": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string"},
                            "query": {"type": "string"},
                            "response": {"type": "string"},
                        },
                        "required": ["query", "response"],
                    },
                    "include_sample_schema": False,
                },
                "testing_criteria": [
                    {
                        "type": "azure_ai_evaluator",
                        "name": "citation_discipline_probe",
                        "evaluator_name": rubric,
                        "evaluator_version": pinned,
                        "initialization_parameters": {"model": judge_model},
                        "data_mapping": {
                            "query": "{{item.query}}",
                            "response": "{{item.response}}",
                        },
                    }
                ],
                "metadata": {"probe": "citation-discipline-fires"},
            },
        )
        eval_id = evaluation["id"]
        print(f"eval created: {eval_id}")

        try:
            run = client.post(
                f"/openai/v1/evals/{eval_id}/runs",
                json_body={
                    "name": "citation-discipline-probe",
                    "data_source": {
                        "type": "jsonl",
                        "source": {
                            "type": "file_content",
                            "content": [{"item": item} for item in ITEMS],
                        },
                    },
                },
            )
            run_id = run["id"]
            print(f"run started : {run_id}\n")

            state: dict = {}
            status = None
            deadline = time.time() + 600
            while time.time() < deadline:
                time.sleep(10)
                state = client.get(f"/openai/v1/evals/{eval_id}/runs/{run_id}")
                status = state.get("status")
                print(f"  status: {status}")
                if status in {"completed", "failed", "canceled"}:
                    break
            else:
                print("timed out")
                return 2

            if status != "completed":
                print(json.dumps(state.get("error") or state, indent=2)[:2000])
                return 2

            return report(client.paged(f"/openai/v1/evals/{eval_id}/runs/{run_id}/output_items"))
        finally:
            client.request("DELETE", f"/openai/v1/evals/{eval_id}")
            print(f"\ncleaned up: deleted {eval_id}")


def report(output: list[dict]) -> int:
    scores: dict[str, float | None] = {}
    print("\n" + "=" * 72)
    for item in output:
        case_id = (item.get("datasource_item") or {}).get("case_id", "?")
        for result in item.get("results") or []:
            scores[case_id] = result.get("score")
            print(f"\n{case_id}: score={result.get('score')} passed={result.get('passed')}")
            reason = (result.get("sample") or {}).get("output") or result.get("reason")
            print(f"  reason: {json.dumps(reason)[:1200]}")

    print("\n" + "=" * 72)
    for arm in ("cites-current", "unsourced", "superseded-as-current"):
        print(f"  {arm:24s}: {scores.get(arm)}")
    print()

    cited = scores.get("cites-current")
    unsourced = scores.get("unsourced")
    stale = scores.get("superseded-as-current")
    if None in (cited, unsourced, stale):
        print("INCONCLUSIVE — an arm produced no score.")
        return 2

    failures = []
    if unsourced >= cited:
        failures.append(
            "A correct figure with NO source named scored as well as a properly "
            "cited one.\n  The 'name your source' rule is not firing."
        )
    if stale >= cited:
        failures.append(
            "The superseded 2025-10 card presented as CURRENT, with the wrong "
            "figure, scored as\n  well as a correct citation. Both "
            "citation_discipline and rate_card_in_effect\n  should have caught "
            "that and neither did."
        )

    if failures:
        print("FAILED:")
        for item in failures:
            print(f"- {item}")
        print("\nDo not describe these dimensions as controls until this separates.")
        return 1

    print(
        "PASSED. An unsourced figure and a superseded-card-as-current both "
        "scored below a\nproperly cited answer. `citation_discipline` is a real "
        "control."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FoundryError as exc:
        print(f"\nFoundry rejected the request:\n{exc}")
        raise SystemExit(2) from exc
