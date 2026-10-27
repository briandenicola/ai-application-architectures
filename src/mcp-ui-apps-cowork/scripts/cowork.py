"""Build and deploy the Microsoft Copilot Cowork path through Task targets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
REPO_URL = "https://github.com/briandenicola/ai-application-architectures"


def run(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE)
    return result.stdout.strip()


def settings() -> dict[str, str]:
    values = json.loads(run("terraform", f"-chdir={ROOT / 'infra'}", "output", "-json", "cowork"))
    for key in ("mcp_url", "project_endpoint"):
        url = urlsplit(values[key])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError(f"{key} must be an HTTPS URL without credentials")
    return values


def check_subscription(values: dict[str, str]) -> None:
    active = json.loads(run("az", "account", "show", "--output", "json"))
    if active["id"] != values["subscription_id"] or active["tenantId"] != values["tenant_id"]:
        raise ValueError("Azure CLI subscription/tenant differs from Terraform; select the deployment account first")
    print(f"Using subscription {active['name']} ({active['id']})", flush=True)


def configure(values: dict[str, str], path: Path) -> None:
    current = {
        "PLUGIN_ID": values["plugin_id"],
        "MCP_URL": values["mcp_url"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{key}={value}\n" for key, value in current.items()), encoding="utf-8")
    print(f"Updated {path} with non-secret connector configuration")


def build_functions() -> None:
    destination = BUILD / "functions"
    destination.mkdir(parents=True, exist_ok=True)
    run(
        str(ROOT / "mcp-server" / "node_modules" / ".bin" / "esbuild"),
        "functions/index.ts", "--bundle", "--platform=node", "--format=esm",
        "--packages=external", f"--outfile={destination / 'dist' / 'index.js'}",
        cwd=ROOT / "mcp-server",
    )
    shutil.copyfile(ROOT / "mcp-server" / "dist" / "wire-review.html", destination / "dist" / "wire-review.html")
    shutil.copyfile(ROOT / "mcp-server" / "functions" / "host.json", destination / "host.json")
    package = json.loads((ROOT / "mcp-server" / "package.json").read_text(encoding="utf-8"))
    package["main"] = "dist/index.js"
    package.pop("scripts", None)
    (destination / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "mcp-server" / "package-lock.json", destination / "package-lock.json")
    run("npm", "ci", "--omit=dev", "--no-audit", "--no-fund", cwd=destination)
    archive_path = BUILD / "banking-functions.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("host.json", "package.json", "package-lock.json", "dist", "node_modules"):
            source = destination / name
            files = sorted(source.rglob("*")) if source.is_dir() else [source]
            for file in files:
                if file.is_file():
                    archive.write(file, file.relative_to(destination).as_posix())
    print(f"Built {archive_path.relative_to(ROOT)}")


def deploy_agent(values: dict[str, str]) -> None:
    definition = {
        "description": "Investigate synthetic banking wire risk; never execute or approve payments.",
        "definition": {
            "kind": "prompt",
            "model": values["model_deployment"],
            "instructions": (ROOT / "agent" / "wire-investigator.txt").read_text(encoding="utf-8"),
        },
    }
    BUILD.mkdir(parents=True, exist_ok=True)
    path = BUILD / "wire-investigator.json"
    path.write_text(json.dumps(definition), encoding="utf-8")
    run(
        "az", "rest", "--method", "post",
        "--url", f"{values['project_endpoint']}/agents/{values['agent_name']}?api-version=v1",
        "--resource", "https://ai.azure.com", "--body", f"@{path}",
    )
    print(f"Registered Foundry prompt agent {values['agent_name']}")


def deploy_functions(values: dict[str, str]) -> None:
    for name in ("banking_app", "gateway_app"):
        print(f"Deploying {values[name]}", flush=True)
        run(
            "az", "functionapp", "deployment", "source", "config-zip",
            "--resource-group", values["resource_group"], "--name", values[name],
            "--src", str(BUILD / "banking-functions.zip"), "--build-remote", "false",
            "--timeout", "180", "--only-show-errors",
        )


def icon(size: int, outline: bool = False) -> bytes:
    def chunk(name: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            u, v = x / size, y / size
            roof = .15 <= u <= .85 and .18 <= v <= .38 and abs(u - .5) <= (v - .18) * 1.75
            base = .16 <= u <= .84 and .72 <= v <= .81
            pillar = .39 <= v <= .69 and any(a <= u <= a + .1 for a in (.23, .45, .67))
            mark = roof or base or pillar
            rows.extend((255, 255, 255, 255) if mark else
                        (0, 0, 0, 0) if outline else (0, 100, 90, 255))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))


def manifest(values: dict[str, str]) -> dict:
    docs = f"{REPO_URL}/blob/main/src/mcp-ui-apps-cowork/README.md"
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.29/MicrosoftTeams.schema.json",
        "manifestVersion": "1.29", "version": "1.0.0", "id": values["plugin_id"],
        "developer": {
            "name": "AI Application Architectures", "websiteUrl": REPO_URL,
            "privacyUrl": f"{docs}#synthetic-data-and-demo-terms",
            "termsOfUseUrl": f"{docs}#synthetic-data-and-demo-terms",
        },
        "name": {"short": "Banking Wire Review", "full": "Banking Wire Review for Microsoft Copilot Cowork"},
        "description": {
            "short": "Review synthetic wire risk with a panel and an Azure Foundry agent.",
            "full": "Review synthetic high-risk wires, investigate risk signals with an Azure Foundry agent, and submit pending hold requests. No payment holds or approvals are executed.",
        },
        "icons": {"color": "color.png", "outline": "outline.png"}, "accentColor": "#00645A",
        "validDomains": [urlsplit(values["mcp_url"]).hostname],
        "agentSkills": [{"folder": "./skills/wire-review"}],
        "agentConnectors": [{
            "id": "banking", "displayName": "Banking tools",
            "description": "Synthetic wire review and Azure Foundry risk investigation",
            "toolSource": {"remoteMcpServer": {
                "mcpServerUrl": values["mcp_url"],
                "authorization": {"type": "None"},
            }},
        }],
    }


def package_plugin(values: dict[str, str]) -> None:
    data = manifest(values)
    subprocess.run(
        ["node", str(ROOT / "cowork" / "validate-manifest.cjs")],
        input=json.dumps(data), text=True, check=True,
    )
    BUILD.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BUILD / "banking-cowork.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(data, indent=2) + "\n")
        archive.writestr("color.png", icon(192))
        archive.writestr("outline.png", icon(32, outline=True))
        skill = ROOT / "cowork" / "skills" / "wire-review" / "SKILL.md"
        archive.write(skill, "skills/wire-review/SKILL.md")
    print("Built .build/banking-cowork.zip")


def verify(values: dict[str, str]) -> None:
    operations = [
        ("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "banking-verifier", "version": "1.0"}}),
        ("tools/list", {}),
        ("tools/call", {"name": "get_high_risk_wires", "arguments": {"minRisk": 80}}),
        ("resources/read", {"uri": "ui://banking/wire-review"}),
    ]
    for index, (method, params) in enumerate(operations, 1):
        request = Request(values["mcp_url"], data=json.dumps({
            "jsonrpc": "2.0", "id": index, "method": method, "params": params,
        }).encode(), headers={
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        })
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if "error" in result or result.get("result", {}).get("isError"):
            raise ValueError(f"{method} failed: {result}")
        payload = result["result"]
        if method == "tools/list":
            tools = {tool["name"]: tool for tool in payload["tools"]}
            if not {"get_high_risk_wires", "create_hold_request", "analyze_wire"} <= tools.keys():
                raise ValueError("Gateway is missing banking/investigation tools")
            if tools["create_hold_request"]["_meta"]["ui"]["visibility"] != ["app"]:
                raise ValueError("Hold request tool is not app-only")
        if method == "tools/call" and len(payload["structuredContent"]["wires"]) != 3:
            raise ValueError("Expected three synthetic wires at risk >= 80")
        if method == "resources/read" and payload["contents"][0]["mimeType"] != "text/html;profile=mcp-app":
            raise ValueError("Expected an MCP App HTML resource")
        print(f"{method}: OK")
    print("Read-only verification complete. Test panel callbacks and the Foundry investigator in Cowork.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["configure", "build", "agent", "deploy", "package", "verify"])
    args = parser.parse_args()
    if args.action == "build":
        build_functions()
        return
    values = settings()
    if args.action in {"agent", "deploy"}:
        check_subscription(values)
    if args.action == "configure":
        configure(values, ROOT / "cowork" / "env" / ".env.local")
    elif args.action == "agent":
        deploy_agent(values)
    elif args.action == "deploy":
        deploy_functions(values)
    elif args.action == "package":
        configure(values, ROOT / "cowork" / "env" / ".env.local")
        package_plugin(values)
    elif args.action == "verify":
        verify(values)


if __name__ == "__main__":
    main()
