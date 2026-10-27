"""Prove the new guards fail closed by disabling one at a time, then restoring."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "mcp-server" / "functions" / "auth.ts"
BANKING = ROOT / "mcp-server" / "functions" / "banking-api.ts"
FOUNDRY = ROOT / "mcp-server" / "functions" / "azure-backend.ts"

CASES = [
    ("tenant", AUTH, 'claims.tid !== config.tenantId', "false"),
    ("delegated scope", AUTH, '!claims.scp.split(" ").includes("access_as_user")', "false"),
    ("gateway caller", AUTH, 'claims.azp !== config.callerId', "false"),
    ("application role", AUTH, '!claims.roles.includes("Banking.Invoke")', "false"),
    ("no delegated backend token", AUTH, 'claims.scp !== undefined', "false"),
    ("persist before success", BANKING, "await record(hold, actor);", ""),
    ("completed Foundry response", FOUNDRY, 'result.status !== "completed"', "false"),
    ("nonempty Foundry answer", FOUNDRY, "if (!text)", "if (false)"),
]


def tests() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["npm", "--prefix", "mcp-server", "test"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def main() -> None:
    baseline = tests()
    if baseline.returncode:
        raise RuntimeError(f"Unmodified tests must pass before tampering:\n{baseline.stdout}")
    for name, path, original, replacement in CASES:
        source = path.read_text(encoding="utf-8")
        if source.count(original) != 1:
            raise RuntimeError(f"{name}: expected exactly one guard to mutate")
        try:
            path.write_text(source.replace(original, replacement), encoding="utf-8")
            result = tests()
            if not result.returncode or "not ok" not in result.stdout:
                raise RuntimeError(f"{name}: expected an assertion failure:\n{result.stdout}")
            print(f"{name}: disabled guard rejected by tests")
        finally:
            path.write_text(source, encoding="utf-8")
    restored = tests()
    if restored.returncode:
        raise RuntimeError(f"Restored tests failed:\n{restored.stdout}")
    print("All guards restored; tests pass.")


if __name__ == "__main__":
    main()
