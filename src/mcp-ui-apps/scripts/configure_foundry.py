"""Populate the local agent configuration for Entra ID authentication."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

from dotenv import dotenv_values, set_key, unset_key


def configure(env_path: Path, values: dict[str, str]) -> None:
    required = ("LLM_MODE", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
    for key in required:
        value = values[key]
        if not isinstance(value, str) or not value.strip() or any(
            char in value for char in "\r\n<>"
        ):
            raise ValueError(f"Invalid Terraform output: {key}")
    endpoint = urlsplit(values["AZURE_OPENAI_ENDPOINT"])
    if values["LLM_MODE"] != "azure" or endpoint.scheme != "https" or not endpoint.hostname:
        raise ValueError("Expected Azure mode and an HTTPS account endpoint")

    if not env_path.exists():
        shutil.copyfile(env_path.with_name(".env.example"), env_path)
    env_path.chmod(0o600)
    for key in required:
        set_key(env_path, key, values[key])
    if "AZURE_OPENAI_API_KEY" in dotenv_values(env_path):
        unset_key(env_path, "AZURE_OPENAI_API_KEY")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["terraform", f"-chdir={root / 'infra'}", "output", "-json", "agent_environment"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    configure(root / "agent" / ".env", json.loads(result.stdout))
    print("Updated agent/.env from Terraform. Restart the stack with task up.")


if __name__ == "__main__":
    main()
