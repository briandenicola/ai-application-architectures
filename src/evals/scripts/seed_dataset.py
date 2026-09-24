#!/usr/bin/env python3
"""Register the golden dataset as a Foundry dataset asset.

Three steps, all REST:
  1. startPendingUpload  -> Foundry hands back a SAS to a MANAGED blob
  2. PUT the JSONL        -> straight to that blob
  3. create the version   -> the dataset becomes a portal asset

Step 1 matters more than it looks. The blob lives in a Microsoft-managed
subscription, not ours, so the tenant policy that forces publicNetworkAccess
Disabled on our own storage accounts (see ADR-0004) does not apply to it. That
is why datasets work here when our own blob corpus did not.

The registered dataset is what the portal's Create-evaluation flow lets you pick
on stage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ROOT,
    console,
    fail,
    load_config,
    ok,
    select_corpus,
    step,
    warn,
)
from _foundry import FoundryClient, FoundryError  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register the golden dataset in Foundry.")
    parser.add_argument("--name", help="Override the dataset name.")
    parser.add_argument("--version", help="Override the dataset version.")
    parser.add_argument(
        "--limit",
        type=int,
        help="Publish only the first N cases. Use this to seed a small dataset for "
        "rehearsing a run without paying for the full golden set.",
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        metavar="CASE_ID",
        help="Publish only these case ids, in dataset order. Unlike --limit this "
        "picks the cases worth running rather than whichever happen to be first. "
        "An id that is not in the dataset is an error, not a smaller dataset.",
    )
    parser.add_argument(
        "--corpus",
        choices=("meridian", "finops"),
        default="meridian",
        help="Which track to operate on. Swaps in the _finops config blocks.",
    )
    args = parser.parse_args()
    if args.cases and args.limit:
        fail("--cases and --limit both select a subset -- pass one or the other")
    return args


def to_eval_items(
    dataset_path: Path,
    limit: int | None = None,
    cases: list[str] | None = None,
) -> str:
    """Flatten the golden dataset into the item shape the eval reads.

    Only fields the evaluation actually consumes are published. Fields used for
    authoring notes stay out of the uploaded asset so the portal view is
    readable during the demo.
    """
    # `is not None`, not truthiness: an empty selection must fail, not quietly
    # fall through to publishing the entire golden set.
    wanted = set(cases) if cases is not None else None
    seen: set[str] = set()

    lines: list[str] = []
    for raw in dataset_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        if limit is not None and len(lines) >= limit:
            break
        row = json.loads(raw)
        if wanted is not None:
            if row["case_id"] not in wanted:
                continue
            seen.add(row["case_id"])
        lines.append(
            json.dumps(
                {
                    "case_id": row["case_id"],
                    "failure_tag": row["failure_tag"],
                    "query": row["query"],
                    "ground_truth": row.get("ground_truth", ""),
                    "must_refuse": row.get("must_refuse", False),
                    "expected_citations": ", ".join(row.get("expected_citations", [])),
                    "forbidden_citations": ", ".join(row.get("forbidden_citations", [])),
                }
            )
        )
    if wanted is not None:
        missing = sorted(wanted - seen)
        if missing:
            # Seeding fewer cases than asked for, silently, would produce a
            # run that looks complete and covers less than it claims.
            fail(f"--cases named {', '.join(missing)}, which are not in {dataset_path.name}")
    if not lines:
        fail(f"no cases selected from {dataset_path.name}")
    return "\n".join(lines) + "\n"


def upload_blob(sas_uri: str, blob_name: str, content: str) -> str:
    """PUT the payload into the container SAS Foundry just issued."""
    base, _, query = sas_uri.partition("?")
    url = f"{base.rstrip('/')}/{blob_name}?{query}"
    response = httpx.put(
        url,
        content=content.encode("utf-8"),
        headers={
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": "application/jsonl",
        },
        timeout=120.0,
    )
    if response.status_code >= 400:
        fail(f"Blob upload failed -> {response.status_code}\n{response.text[:800]}")
    return url.split("?")[0]


def main() -> int:
    args = parse_args()
    config = select_corpus(load_config(), args.corpus)
    dataset_cfg = config["dataset"]
    dataset_path = ROOT / dataset_cfg["path"]
    if not dataset_path.exists():
        fail(f"Dataset not found: {dataset_path}")

    name = args.name or dataset_cfg["name"]
    version = str(args.version or dataset_cfg.get("version", "1"))
    payload = to_eval_items(dataset_path, args.limit, args.cases)
    case_count = len(payload.strip().splitlines())

    console.print()
    console.rule("[bold]Foundry dataset")

    with FoundryClient(config["project"]["endpoint"]) as client:
        step(f"Requesting upload location for '{name}' v{version}")
        try:
            pending = client.post(
                f"/datasets/{name}/versions/{version}/startPendingUpload",
                json_body={"pendingUploadType": "BlobReference"},
            )
        except FoundryError as exc:
            fail(f"Could not start pending upload:\n{exc}")

        blob = pending["blobReference"]
        sas_uri = blob["credential"]["sasUri"]

        step(f"Uploading {case_count} cases")
        blob_uri = upload_blob(sas_uri, f"{name}.jsonl", payload)

        step("Registering dataset version")
        try:
            registered = client.request(
                "PUT",
                f"/datasets/{name}/versions/{version}",
                json_body={
                    "type": "uri_file",
                    "dataUri": blob_uri,
                    "description": f"Meridian golden evaluation set — {case_count} cases",
                    "tags": {"demo": "meridian-foundry-evals"},
                },
            )
        except FoundryError as exc:
            fail(f"Could not register dataset version:\n{exc}")

    dataset_id = registered.get("id", "")
    ok(f"Dataset '{name}' v{version} registered — {case_count} cases")
    console.print(f"  [dim]{dataset_id}[/dim]")
    if not dataset_id:
        warn("No dataset id returned; the evaluation run will not be able to reference it.")
    ok("Selectable in the portal under Evaluations → Create → Dataset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
