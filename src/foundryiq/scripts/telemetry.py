"""Response diagnostics and Entra-authenticated Foundry trace queries."""

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

AUDIENCE = "https://api.applicationinsights.io"


def wait_seconds():
    seconds = int(os.environ.get("TRACE_WAIT_SECONDS", "120"))
    if seconds < 0:
        raise ValueError("TRACE_WAIT_SECONDS must be a nonnegative integer.")
    return seconds


def validate_response_id(response_id):
    if not isinstance(response_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", response_id):
        raise ValueError("Supply the response ID printed by task ask, not a URL or query.")
    return response_id


def require_configuration(config):
    if not config.get("application_insights_app_id") or not config.get("application_insights_id"):
        raise RuntimeError("Run task up to provision and connect Application Insights first.")


def trace_query(response_id):
    response_id = validate_response_id(response_id)
    return f"""let telemetry = materialize(
    union withsource=telemetryTable dependencies, requests, traces, exceptions, customEvents
    | where timestamp > ago(24h)
);
let operations = telemetry
    | where tostring(customDimensions["gen_ai.response.id"]) == {json.dumps(response_id)}
    | where isnotempty(operation_Id)
    | distinct operation_Id;
telemetry
| where operation_Id in (operations)
| project timestamp, telemetryTable, operation_Id,
    spanId=tostring(column_ifexists("id", "")),
    parentSpanId=tostring(column_ifexists("operation_ParentId", "")),
    name=tostring(column_ifexists("name", "")),
    operation=tostring(customDimensions["gen_ai.operation.name"]),
    model=tostring(customDimensions["gen_ai.response.model"]),
    inputTokens=tolong(customDimensions["gen_ai.usage.input_tokens"]),
    outputTokens=tolong(customDimensions["gen_ai.usage.output_tokens"]),
    durationMs=todouble(column_ifexists("duration", real(null))),
    success=tostring(column_ifexists("success", "")),
    resultCode=tostring(column_ifexists("resultCode", "")),
    tool=tostring(customDimensions["gen_ai.tool.name"]),
    message=coalesce(tostring(column_ifexists("message", "")),
                     tostring(column_ifexists("outerMessage", ""))),
    dimensions=customDimensions
| order by timestamp asc
| take 201"""


def query_rows(result):
    if result.get("error"):
        raise RuntimeError(
            f"Application Insights query failed or was partial: {json.dumps(result['error'])}"
        )
    tables = result.get("tables")
    if not isinstance(tables, list):
        raise RuntimeError("Application Insights query returned no result tables.")
    table = next((table for table in tables if table.get("name") == "PrimaryResult"), None)
    if table is None:
        raise RuntimeError("Application Insights query returned no PrimaryResult table.")
    columns = [column["name"] for column in table["columns"]]
    rows = []
    for values in table["rows"]:
        if len(values) != len(columns):
            raise RuntimeError("Application Insights query returned a malformed row.")
        rows.append(dict(zip(columns, values, strict=True)))
    return rows


def response_summary(response, elapsed):
    return {
        "response_id": response.get("id"),
        "elapsed_seconds": round(elapsed, 2),
        "model": response.get("model"),
        "usage": response.get("usage"),
        "mcp_calls": [
            {
                key: item[key]
                for key in ("id", "name", "status", "arguments", "output", "error")
                if key in item
            }
            for item in response.get("output", [])
            if item.get("type") == "mcp_call"
        ],
    }


def print_summary(summary):
    usage = summary["usage"]
    print(
        f"\nResponse: {summary['response_id'] or 'not supplied'}; "
        f"elapsed: {summary['elapsed_seconds']}s; model: {summary['model'] or 'not supplied'}"
    )
    print(f"Tokens: {json.dumps(usage) if usage is not None else 'not supplied by the service'}")
    for call in summary["mcp_calls"]:
        print(
            f"MCP: {call.get('name', 'unnamed')} [{call.get('status', 'not supplied')}] "
            f"id={call.get('id', 'not supplied')}"
        )
        for field in ("arguments", "output", "error"):
            if call.get(field) is None:
                continue
            value = call[field]
            preview = value if isinstance(value, str) else json.dumps(value)
            suffix = " [truncated; see artifact]" if len(preview) > 800 else ""
            print(f"  {field.capitalize()}: {preview[:800]}{suffix}")


def report(client, config, response_id, root, record=None):
    require_configuration(config)
    response_id = validate_response_id(response_id)
    seconds = wait_seconds()
    query = trace_query(response_id)
    path = Path(root) / ".artifacts" / "traces" / f"{response_id}.json"
    if record is None:
        record = json.loads(path.read_text()) if path.exists() else {}
    record["telemetry"] = {
        "status": "querying",
        "query": query,
        "application_insights_id": config["application_insights_id"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Diagnostics artifact: {path}", flush=True)
    print(f"Checking correlated App Insights telemetry (up to {seconds}s)...", flush=True)
    app_id = quote(config["application_insights_app_id"], safe="")
    deadline = time.monotonic() + seconds
    try:
        while True:
            result = client.request(
                "POST",
                f"https://api.applicationinsights.io/v1/apps/{app_id}/query",
                AUDIENCE,
                {"query": query, "timespan": "PT24H"},
                timeout=min(30, max(1, deadline - time.monotonic())) if seconds else 30,
            )
            rows = query_rows(result)
            remaining = deadline - time.monotonic()
            if rows or remaining <= 0:
                break
            time.sleep(min(10, remaining))
            if time.monotonic() >= deadline:
                break
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        record["telemetry"].update(status="error", error=str(error))
        path.write_text(json.dumps(record, indent=2) + "\n")
        raise
    truncated = len(rows) > 200
    record["telemetry"].update(
        status="observed" if rows else "pending",
        records=rows[:200],
        truncated=truncated,
    )
    path.write_text(json.dumps(record, indent=2) + "\n")
    if not rows:
        print(
            f"Traces pending: no correlated records yet. Retry without another model call:\n"
            f"task traces -- {response_id}",
            flush=True,
        )
        return
    print(f"Traces observed: {min(len(rows), 200)} records. Additional spans may arrive later.")
    for row in rows[:200]:
        print(
            f"  {row.get('timestamp')} {row.get('telemetryTable')} "
            f"{row.get('operation') or row.get('name') or ''} "
            f"duration={row.get('durationMs')}ms success={row.get('success') or 'not supplied'} "
            f"trace={row.get('operation_Id')} span={row.get('spanId')}"
        )
        if row.get("message"):
            message = str(row["message"])
            print(
                f"    {message[:800]}{' [truncated; see artifact]' if len(message) > 800 else ''}"
            )
    if truncated:
        print("Trace output limited to 200 records; query in the artifact can be expanded.")
