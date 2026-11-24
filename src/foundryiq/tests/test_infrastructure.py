import re
import subprocess
import unittest

from scripts import demo


class InfrastructureTests(unittest.TestCase):
    def test_foundry_child_writes_are_serialized(self):
        result = subprocess.run(
            ["terraform", "-chdir=infra", "graph"],
            cwd=demo.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        edges = re.findall(r'"([^"]+)" -> "([^"]+)"', result.stdout)
        dependencies = {}
        for resource, dependency in edges:
            dependencies.setdefault(resource, set()).add(dependency)

        def depends_on(resource, target):
            pending = list(dependencies.get(resource, set()))
            visited = set()
            while pending:
                dependency = pending.pop()
                if dependency == target:
                    return True
                if dependency not in visited:
                    visited.add(dependency)
                    pending.extend(dependencies.get(dependency, set()))
            return False

        for resource, dependency in [
            ("azapi_resource.project", "azapi_resource.foundry"),
            ("azapi_resource.chat_model", "azapi_resource.project"),
            ("azapi_resource.embedding_model", "azapi_resource.chat_model"),
        ]:
            with self.subTest(resource=resource, dependency=dependency):
                self.assertTrue(
                    depends_on(resource, dependency),
                    f"{resource} must wait for {dependency}",
                )
