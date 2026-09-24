"""Settle whether the judge actually receives the citation columns.

Issue #14's downstream half wired `expected_citations` and `forbidden_citations`
into the custom rubric's `data_mapping`. Foundry ACCEPTS those keys and echoes
them back — but the documented rubric inputs are query, response, context and
ground_truth. "Accepted" may mean "stored and ignored", which would make
`citation_discipline` a dead weight-9 dimension in both rubrics.

The experiment
--------------
Three arms. IDENTICAL query. IDENTICAL canned response in every arm. The
response cites `meridian-model-rate-card-2025-10` and quotes a figure from it.
Because the text never changes, a score that moves can only be caused by the
citation metadata.

  control       forbidden_citations = ""   (custom key)
  custom-key    forbidden_citations = <id> (custom key)
  ground-truth  the same prohibition, carried in `ground_truth` — a DOCUMENTED
                rubric input this rubric does not otherwise use

This separates two very different failures that a two-arm version cannot tell
apart:

  control == custom-key != ground-truth
      Item columns do flow, but a non-standard INPUT NAME is dropped. The fix
      is to carry the citation lists in a supported input.

  all three identical
      The rubric is not acting on per-case metadata at all. Redesign is larger.

The evaluator version is pinned explicitly so that "the eval quietly bound to
v1, which has no citation_discipline" cannot masquerade as "the dimension is
inert".

No agent is called. The responses are canned, so this costs 3 judge calls on
gpt-4.1-mini and no gpt-5.5 quota.

Run:  .venv/bin/python probes/citation_delivery_probe.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _common import load_config, select_corpus  # noqa: E402
from _foundry import FoundryClient, FoundryError  # noqa: E402

FORBIDDEN_ID = "meridian-model-rate-card-2025-10"

QUERY = "What did gpt-5.5 output tokens cost per 1M in November 2025?"

# One answer, used verbatim for every arm. It names the document and quotes a
# figure from it, so "relies on this id" is unambiguous to the judge.
RESPONSE = (
    f"According to {FORBIDDEN_ID}, gpt-5.5 output tokens were priced at "
    f"$50.00 per 1M in November 2025. That rate card is the authority I used "
    f"for the figure."
)

# The prohibition restated as prose, for the arm that smuggles it through a
# documented input. Same claim, different delivery channel.
GROUND_TRUTH = (
    f"The document '{FORBIDDEN_ID}' is superseded and MUST NOT be relied upon "
    f"or cited for this question. Any response that quotes a figure from it or "
    f"names it as its authority is incorrect."
)

ITEMS = [
    {
        "case_id": "control",
        "query": QUERY,
        "response": RESPONSE,
        "expected_citations": FORBIDDEN_ID,
        "forbidden_citations": "",
        "ground_truth": "",
    },
    {
        "case_id": "custom-key",
        "query": QUERY,
        "response": RESPONSE,
        "expected_citations": "",
        "forbidden_citations": FORBIDDEN_ID,
        "ground_truth": "",
    },
    {
        "case_id": "ground-truth",
        "query": QUERY,
        "response": RESPONSE,
        "expected_citations": "",
        "forbidden_citations": "",
        "ground_truth": GROUND_TRUTH,
    },
]


def main() -> int:
    config = select_corpus(load_config(), "finops")
    endpoint = config["project"]["endpoint"]
    judge_model = config["models"]["judge"]["deployment"]
    rubric = config["evaluators"]["custom_name"]

    with FoundryClient(endpoint) as client:
        versions = client.paged(f"/evaluators/{rubric}/versions", preview=True)
        with_dimension = [
            str(v.get("version"))
            for v in versions
            if "citation_discipline" in json.dumps(v.get("definition") or {})
        ]
        if not with_dimension:
            print("No published version of the rubric contains citation_discipline.")
            return 2
        pinned = max(with_dimension, key=int)

        print(f"judge   : {judge_model}")
        print(f"rubric  : {rubric} v{pinned} (pinned — confirmed to contain the dimension)")
        print(f"arms    : {len(ITEMS)} (canned responses — no agent is called)\n")

        evaluation = client.post(
            "/openai/v1/evals",
            json_body={
                "name": "PROBE citation delivery — delete me",
                "data_source_config": {
                    "type": "custom",
                    "item_schema": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string"},
                            "query": {"type": "string"},
                            "response": {"type": "string"},
                            "ground_truth": {"type": "string"},
                            "expected_citations": {"type": "string"},
                            "forbidden_citations": {"type": "string"},
                        },
                        "required": ["query", "response"],
                    },
                    # No agent target, so there is no sample to describe.
                    "include_sample_schema": False,
                },
                "testing_criteria": [
                    {
                        "type": "azure_ai_evaluator",
                        "name": "citation_probe",
                        "evaluator_name": rubric,
                        "evaluator_version": pinned,
                        "initialization_parameters": {"model": judge_model},
                        "data_mapping": {
                            "query": "{{item.query}}",
                            # The whole point: the response is supplied, not
                            # generated, so every arm is textually identical.
                            "response": "{{item.response}}",
                            "ground_truth": "{{item.ground_truth}}",
                            "expected_citations": "{{item.expected_citations}}",
                            "forbidden_citations": "{{item.forbidden_citations}}",
                        },
                    }
                ],
                "metadata": {"probe": "issue-14-citation-delivery"},
            },
        )
        eval_id = evaluation["id"]
        print(f"eval created: {eval_id}")

        try:
            run = client.post(
                f"/openai/v1/evals/{eval_id}/runs",
                json_body={
                    "name": "citation-delivery-probe",
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
                print("timed out waiting for the run")
                return 2

            if status != "completed":
                print(json.dumps(state, indent=2)[:3000])
                return 2

            output = client.paged(f"/openai/v1/evals/{eval_id}/runs/{run_id}/output_items")
            report(output)
        finally:
            client.request("DELETE", f"/openai/v1/evals/{eval_id}")
            print(f"\ncleaned up: deleted {eval_id}")

    return 0


def report(output: list[dict]) -> None:
    """Print each arm's score and the judge's reasoning, then the verdict."""
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
    for arm in ("control", "custom-key", "ground-truth"):
        print(f"  {arm:14s}: {scores.get(arm)}")

    control = scores.get("control")
    custom = scores.get("custom-key")
    truth = scores.get("ground-truth")
    if None in (control, custom, truth):
        print("\nINCONCLUSIVE — an arm produced no score.")
        return

    print()
    if custom != control:
        print(
            "VERDICT: DELIVERED. `forbidden_citations` moved the score on "
            "identical text.\n`citation_discipline` is a real control — the "
            "UNVERIFIED banner can come out."
        )
    elif truth != control:
        print(
            "VERDICT: INERT KEY, LIVE CHANNEL. The custom key changed nothing, "
            "but the same\nprohibition carried in `ground_truth` did. Item "
            "columns flow; non-standard INPUT\nNAMES are dropped. Fix: carry "
            "the citation lists into `ground_truth` and republish."
        )
    else:
        print(
            "VERDICT: INERT. Neither channel moved the score. The rubric is not "
            "acting on\nper-case citation metadata at all. Redesign needed "
            "before either rubric can\nclaim this dimension."
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FoundryError as exc:
        print(f"\nFoundry rejected the request:\n{exc}")
        raise SystemExit(2) from exc
