#!/usr/bin/env python3
"""Create or update the v1 and v2 prompt agents from their YAML definitions.

Idempotent. The agent definitions are the version-controlled artifacts; the
Foundry-side agents are derived from them and never edited by hand. If someone
tweaks a prompt in the portal, the next run of this script overwrites it — which
is the behaviour you want when the prompt is the thing under evaluation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from _common import ROOT, ConfigError, console, fail, get_credential, load_config, ok, step

STATE_FILE = ROOT / ".azure" / "agents.json"


def resolve_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_env(v) for v in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        name = value[2:-1]
        resolved = os.environ.get(name)
        if resolved is None:
            raise ConfigError(f"Agent definition references unset variable {name}")
        return resolved
    return value


def load_agent_definition(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return resolve_env(yaml.safe_load(handle))


def definition_revision(path: Path) -> str:
    """Hash the raw file, not the resolved dict — the recorded revision must refer
    to what a reviewer can read in a PR."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build_definition(definition: dict[str, Any], connection_id: str) -> Any:
    """Translate the version-controlled YAML into a PromptAgentDefinition.

    Grounding goes through the `azure_ai_search` tool, which resolves the index
    via a project connection. There is no knowledge-base tool at this API
    version — see docs/adr/0005-agent-grounding-via-search-connection.md.
    """
    from azure.ai.projects.models import (
        AISearchIndexResource,
        AzureAISearchTool,
        AzureAISearchToolResource,
        PromptAgentDefinition,
    )

    model = definition["model"]
    retrieval = definition["knowledge"]["retrieval"]

    # temperature/top_p are only sent when the YAML declares them. Reasoning
    # models (gpt-5.5) reject both, and the service rejects the whole request —
    # so an unconditional temperature=0.0 breaks every grounded question.
    sampling = {k: model[k] for k in ("temperature", "top_p") if k in model}

    return PromptAgentDefinition(
        model=model["deployment"],
        instructions=definition["instructions"],
        **sampling,
        tools=[
            AzureAISearchTool(
                azure_ai_search=AzureAISearchToolResource(
                    indexes=[
                        AISearchIndexResource(
                            project_connection_id=connection_id,
                            index_name=definition["knowledge"]["index"],
                            query_type=retrieval["query_type"],
                            top_k=retrieval["max_docs"],
                        )
                    ]
                )
            )
        ],
    )


def latest_revision(project: Any, name: str) -> str | None:
    """Return the definition revision recorded on the newest version, if any."""
    from azure.core.exceptions import ResourceNotFoundError

    try:
        versions = list(project.agents.list_versions(agent_name=name, limit=1, order="desc"))
    except ResourceNotFoundError:
        return None
    if not versions:
        return None
    return (versions[0].metadata or {}).get("definition_revision")


def smoke_test(project: Any, name: str, model: str, question: str) -> None:
    """Prove the agent can actually answer a grounded question.

    This exists because the agent API does NOT validate tools at creation time.
    A tool block with a typo, a missing connection, or a deleted index all
    produce a perfectly successful create and an agent that fails on its first
    question — on stage, in front of the client. Verified 2026-09-21: the API
    accepted a tool of type "totally_bogus_xyz" without complaint.
    """
    step(f"Smoke-testing '{name}' with a grounded question")
    client = project.get_openai_client(agent_name=name)

    # Role assignments on the Search data plane took ~5 minutes to take effect in
    # testing, and the failure they produce is a generic "Access denied" that
    # names no identity. Retrying beats failing the deploy on a timing artefact —
    # but we still fail in the end rather than declaring a broken agent healthy.
    deadline = time.monotonic() + 600
    attempt = 0
    while True:
        attempt += 1
        try:
            response = client.responses.create(input=question, model=model)
            break
        except Exception as exc:  # noqa: BLE001 - any failure here means a dead demo
            retryable = "Access denied" in str(exc) or "tool_user_error" in str(exc)
            if retryable and time.monotonic() < deadline:
                console.print(
                    f"  [dim]attempt {attempt}: waiting for search RBAC to propagate…[/dim]"
                )
                time.sleep(30)
                continue
            fail(
                f"Agent '{name}' was created but cannot answer: {exc}\n"
                "The agent API does not validate tools at creation, so this is "
                "where a broken grounding configuration surfaces. Check that the "
                "Foundry ACCOUNT identity holds Search Index Data Contributor and "
                "Search Service Contributor on the search service (ADR-0005)."
            )

    text = (getattr(response, "output_text", "") or "").strip()
    if not text:
        fail(f"Agent '{name}' returned an empty response to '{question}'.")
    console.print(f"  [dim]{text[:160].replace(chr(10), ' ')}…[/dim]")
    ok(f"Agent '{name}' answered a grounded question")


def main() -> int:
    config = load_config()
    endpoint = config["project"]["endpoint"]

    connection_id = os.environ.get("AZURE_SEARCH_CONNECTION_ID")
    if not connection_id:
        raise ConfigError(
            "AZURE_SEARCH_CONNECTION_ID is not set. It is an output of the Bicep "
            "deployment; run `azd provision` or `azd env refresh` first."
        )

    # Imported lazily so that --help and unit tests do not require the SDK.
    from azure.ai.projects import AIProjectClient

    # allow_preview is required for get_openai_client(agent_name=...), which the
    # smoke test depends on.
    credential = get_credential()
    project = AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True)

    state: dict[str, dict[str, str]] = {}
    smoke_question = config["knowledge"].get("smoke_question", "What is Meridian's advisory fee?")

    for entry in config["agents"]:
        definition_path = ROOT / entry["definition"]
        if not definition_path.exists():
            fail(f"Agent definition not found: {definition_path}")

        definition = load_agent_definition(definition_path)
        name = definition["name"]
        revision = definition_revision(definition_path)

        if latest_revision(project, name) == revision:
            step(f"Agent '{name}' already matches {revision} — skipping")
        else:
            step(f"Publishing agent '{name}' ({revision})")
            version = project.agents.create_version(
                agent_name=name,
                definition=build_definition(definition, connection_id),
                description=definition.get("description", ""),
                metadata={
                    "definition_revision": revision,
                    "model_version": definition["model"]["version"],
                    "include_citations": str(
                        definition["knowledge"]["retrieval"]["include_citations"]
                    ).lower(),
                },
            )
            console.print(f"  [dim]{name} → version {version.version}[/dim]")

        smoke_test(project, name, definition["model"]["deployment"], smoke_question)
        state[name] = {"revision": revision}

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    ok(f"{len(state)} agents published and smoke-tested")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        fail(str(exc))
