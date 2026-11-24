import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"


class TeardownTests(unittest.TestCase):
    def run_down(self, root, *, azure_exit=0, locked=False):
        shutil.copyfile(ROOT / "Taskfile.yaml", root / "Taskfile.yaml")
        (root / "scripts").mkdir()
        (root / "scripts/demo.py").write_text("print('synthetic-group')\n")
        infra = root / "infra"
        infra.mkdir()
        for directory in (".terraform", "terraform.tfstate.d"):
            (infra / directory).mkdir()
            (infra / directory / "synthetic").write_text("fixture")
        for name in ("terraform.tfstate", "terraform.tfstate.backup", ".terraform.lock.hcl"):
            (infra / name).write_text("fixture")
        if locked:
            (infra / ".terraform.tfstate.lock.info").write_text("fixture")
        tools = root / "tools"
        tools.mkdir()
        az = tools / "az"
        az.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['AZ_CALL_LOG']).write_text('\\n'.join(sys.argv[1:]))\n"
            "sys.exit(int(os.environ['AZ_EXIT_CODE']))\n"
        )
        az.chmod(0o755)
        return subprocess.run(
            ["task", "--silent", "down"],
            cwd=root,
            env={
                **os.environ,
                "AZURE_SUBSCRIPTION_ID": SUBSCRIPTION,
                "AZ_CALL_LOG": str(root / "azure-call"),
                "AZ_EXIT_CODE": str(azure_exit),
                "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
            },
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_async_deletion_cleans_state_only_after_azure_accepts(self):
        for azure_exit in (0, 1):
            with self.subTest(azure_exit=azure_exit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = self.run_down(root, azure_exit=azure_exit)
                self.assertEqual(result.returncode == 0, azure_exit == 0, result.stderr)
                self.assertEqual(
                    (root / "azure-call").read_text().splitlines(),
                    [
                        "group",
                        "delete",
                        "--subscription",
                        SUBSCRIPTION,
                        "--name",
                        "synthetic-group",
                        "--yes",
                        "--no-wait",
                    ],
                )
                for name in (
                    ".terraform",
                    "terraform.tfstate.d",
                    "terraform.tfstate",
                    "terraform.tfstate.backup",
                ):
                    self.assertEqual((root / "infra" / name).exists(), azure_exit != 0, name)
                self.assertTrue((root / "infra/.terraform.lock.hcl").exists())

    def test_state_lock_blocks_deletion_and_local_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_down(root, locked=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("state lock", result.stderr)
            self.assertFalse((root / "azure-call").exists())
            self.assertTrue((root / "infra/terraform.tfstate").exists())
            self.assertTrue((root / "infra/.terraform").exists())
