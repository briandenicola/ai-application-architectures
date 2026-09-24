"""Can `messages` carry retrieved context to the rubric judge?

Background
----------
`probes/citation_delivery_probe.py` proved that a `type: rubric` evaluator
accepts exactly four inputs — query, response, messages, tool_definitions —
and silently discards everything else. That killed `citation_discipline`
(weight 9 in both rubrics) and exposed a second problem: `attributed_figures`
(compliance, weight 10) and `no_fabricated_figures` (finops, weight 10) both
instruct the judge to check every figure against "the retrieved context", and
`context` is not an accepted input either. That check has never run.

`messages` IS accepted. If retrieved documents can be delivered through it,
both problems are repairable at once: the judge could finally see what the
agent actually retrieved.

The experiment
--------------
Two arms. IDENTICAL query. IDENTICAL assistant response in both — the response
claims gpt-5.5 output cost **$50.00** per 1M in November 2025. Only the
retrieved context carried in `messages` differs:

  grounded    the context contains the 2025-10 card, which does say $50.00
  ungrounded  the context contains ONLY the 2026-01 card, which says $40.00

Under `no_fabricated_figures` the ungrounded arm must score low: the figure
appears in no retrieved document. Under `rate_card_in_effect` both arms are
fine, because $50.00 IS the correct November rate — that dimension is
deliberately not the one under test, so a score that moves can only have come
from the traceability check reading `messages`.

  scores differ    -> `messages` is a live channel. Both weight-10 dimensions
                      can be repaired, and citation_discipline gets a real home.
  scores identical -> `messages` is inert too. Fall back to baking the facts
                      into the dimension prose, the way rate_card_in_effect
                      already does.

No agent is called: 2 judge calls on gpt-4.1-mini, no gpt-5.5 quota.

Run:  .venv/bin/python probes/messages_channel_probe.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _common import load_config, select_corpus  # noqa: E402
from _foundry import FoundryClient, FoundryError  # noqa: E402

QUERY = "What did gpt-5.5 output tokens cost per 1M in November 2025?"

# Identical in both arms. States $50.00 and attributes it.
RESPONSE = (
    "gpt-5.5 output tokens were priced at $50.00 per 1M in November 2025, "
    "per the rate card in effect for that period."
)

# The arm where the stated figure IS in the retrieved context.
GROUNDED_CONTEXT = (
    "Retrieved documents:\n\n"
    "doc_id: meridian-model-rate-card-2025-10\n"
    "Title: Meridian Model Rate Card (October 2025)\n"
    "gpt-5.5 — input $12.50 / 1M, cached input $1.25 / 1M, output $50.00 / 1M.\n"
)

# The arm where it is NOT. Only the 2026 card was retrieved, and it says
# $40.00 — so $50.00 appears in no retrieved document.
UNGROUNDED_CONTEXT = (
    "Retrieved documents:\n\n"
    "doc_id: meridian-model-rate-card-2026-01\n"
    "Title: Meridian Model Rate Card (January 2026)\n"
    "gpt-5.5 — input $10.00 / 1M, cached input $1.00 / 1M, output $40.00 / 1M.\n"
)


def conversation(context: str) -> list[dict[str, str]]:
    """A three-turn conversation standing in for a retrieval-augmented run."""
    return [
        {"role": "system", "content": context},
        {"role": "user", "content": QUERY},
        {"role": "assistant", "content": RESPONSE},
    ]


ITEMS = [
    # `query` and `response` are deliberately ABSENT. The validator requires
    # every supported field present in the inline data to be mapped, and
    # mapping them alongside `messages` is rejected as mixing the two modes —
    # so in unified-messages mode the conversation must be the only carrier.
    {
        "case_id": "grounded",
        "messages": conversation(GROUNDED_CONTEXT),
    },
    {
        "case_id": "ungrounded",
        "messages": conversation(UNGROUNDED_CONTEXT),
    },
]


def main() -> int:
    config = select_corpus(load_config(), "finops")
    endpoint = config["project"]["endpoint"]
    judge_model = config["models"]["judge"]["deployment"]
    rubric = config["evaluators"]["custom_name"]

    with FoundryClient(endpoint) as client:
        versions = client.paged(f"/evaluators/{rubric}/versions", preview=True)
        pinned = str(max(int(v["version"]) for v in versions))

        print(f"judge : {judge_model}")
        print(f"rubric: {rubric} v{pinned}")
        print(f"arms  : {len(ITEMS)} — identical response, different retrieved context\n")

        evaluation = client.post(
            "/openai/v1/evals",
            json_body={
                "name": "PROBE messages channel — delete me",
                "data_source_config": {
                    "type": "custom",
                    "item_schema": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string"},
                            "messages": {"type": "array"},
                        },
                        "required": ["messages"],
                    },
                    "include_sample_schema": False,
                },
                "testing_criteria": [
                    {
                        "type": "azure_ai_evaluator",
                        "name": "messages_probe",
                        "evaluator_name": rubric,
                        "evaluator_version": pinned,
                        "initialization_parameters": {"model": judge_model},
                        "data_mapping": {
                            # The service rejects mixing `messages` with
                            # `query`/`response` — they are two distinct modes,
                            # "unified-messages" and "legacy request/response".
                            # So the conversation must carry the question and
                            # the answer itself, which it does.
                            "messages": "{{item.messages}}",
                        },
                    }
                ],
                "metadata": {"probe": "messages-channel"},
            },
        )
        eval_id = evaluation["id"]
        print(f"eval created: {eval_id}")

        try:
            run = client.post(
                f"/openai/v1/evals/{eval_id}/runs",
                json_body={
                    "name": "messages-channel-probe",
                    # Required whenever the item_schema is unified-messages.
                    # Valid values are 'turn' and 'conversation'; the rubric
                    # judges one exchange at a time, and rejects conversation-level.
                    "evaluation_level": "turn",
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
                print("\n--- failure detail ---")
                for key in ("error", "result_counts", "status_details", "message"):
                    if state.get(key):
                        print(f"{key}: {json.dumps(state[key], indent=2)[:1500]}")
                items = client.paged(f"/openai/v1/evals/{eval_id}/runs/{run_id}/output_items")
                for item in items[:2]:
                    print(json.dumps(item, indent=2)[:1500])
                return 2

            report(client.paged(f"/openai/v1/evals/{eval_id}/runs/{run_id}/output_items"))
        finally:
            client.request("DELETE", f"/openai/v1/evals/{eval_id}")
            print(f"\ncleaned up: deleted {eval_id}")

    return 0


def report(output: list[dict]) -> None:
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
    grounded = scores.get("grounded")
    ungrounded = scores.get("ungrounded")
    print(f"  grounded   (figure IS in context) : {grounded}")
    print(f"  ungrounded (figure is NOT)        : {ungrounded}")
    print()

    if grounded is None or ungrounded is None:
        print("INCONCLUSIVE — an arm produced no score.")
    elif grounded == ungrounded:
        print(
            "VERDICT: INERT. The judge scored an untraceable figure exactly as "
            "it scored a\ntraceable one. `messages` does not reach it either.\n"
            "Fall back to baking the facts into the dimension prose, as "
            "rate_card_in_effect does."
        )
    else:
        print(
            "VERDICT: LIVE CHANNEL. Retrieved context delivered through "
            "`messages` moved the\nscore on an identical response. Both "
            "weight-10 figure dimensions can be repaired,\nand "
            "citation_discipline has a real home."
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FoundryError as exc:
        print(f"\nFoundry rejected the request:\n{exc}")
        raise SystemExit(2) from exc
