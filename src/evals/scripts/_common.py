"""Shared helpers: config loading, env resolution, console output.

Every script reads Azure configuration from the environment (populated by `azd`)
and tunables from `evals.config.yaml`. Nothing environment-specific is hardcoded.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

ROOT = Path(__file__).resolve().parent.parent
console = Console()

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


class ConfigError(RuntimeError):
    """Raised when configuration or environment is missing or malformed.

    Callers exit with code 2 on this, never 1 — an unrunnable harness is an
    infrastructure problem, not a quality failure. Conflating the two would let a
    broken pipeline masquerade as a failing gate.
    """


def _resolve(value: Any) -> Any:
    """Recursively substitute ${ENV_VAR} references."""
    if isinstance(value, dict):
        return {k: _resolve(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v) for v in value]
    if not isinstance(value, str):
        return value

    def sub(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        resolved = os.environ.get(name, default)
        if resolved is None:
            raise ConfigError(
                f"Environment variable {name} is not set and has no default. "
                f"Run 'azd env refresh' or check infra/main.bicep outputs."
            )
        return resolved

    return _ENV_PATTERN.sub(sub, value)


def load_config(path: str | Path = "evals.config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    if not config_path.exists():
        raise ConfigError(f"Config not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        return _resolve(yaml.safe_load(handle))


def get_credential() -> Any:
    """Keyless auth. Azure CLI first — it is what a presenter is actually logged
    in as — falling back to the default chain for CI.

    Imported lazily so that the pure-logic modules (and the quality-gate tests
    that exercise them) do not require the Azure SDK to be installed.
    """
    from azure.identity import (
        AzureCliCredential,
        ChainedTokenCredential,
        DefaultAzureCredential,
    )

    return ChainedTokenCredential(AzureCliCredential(), DefaultAzureCredential())


def require_env(*names: str) -> dict[str, str]:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise ConfigError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nThese come from infra/main.bicep outputs. Try: azd env refresh"
        )
    return {n: os.environ[n] for n in names}


def fail(message: str, code: int = 2) -> None:
    """Exit with a distinguishable code. 2 = cannot run, 1 = quality gate failed."""
    console.print(f"[bold red]✗[/bold red] {message}")
    sys.exit(code)


def ok(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def step(message: str) -> None:
    console.print(f"[bold cyan]→[/bold cyan] {message}")


def warn(message: str) -> None:
    console.print(f"[bold yellow]![/bold yellow] {message}")
