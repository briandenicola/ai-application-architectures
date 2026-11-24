import base64
import gzip
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    bundle = json.loads(gzip.decompress(base64.b64decode(sys.argv[1])))
    config = bundle["config"]
    with tempfile.TemporaryDirectory(prefix="foundryiq-worker-") as directory:
        root = Path(directory)
        for name, content in bundle["files"].items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        subprocess.run(
            [
                "az",
                "login",
                "--identity",
                "--client-id",
                config["setup_runner_client_id"],
                "--allow-no-subscriptions",
                "--output",
                "none",
            ],
            check=True,
        )
        result = subprocess.run(
            [sys.executable, str(root / "scripts/demo.py"), "worker"],
            cwd=root,
            env={**os.environ, "DEMO_CONFIGURATION": json.dumps(config)},
            check=False,
        )
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
