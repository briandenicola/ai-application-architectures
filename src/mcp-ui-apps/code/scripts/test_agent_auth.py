import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


class AgentAuthTests(unittest.TestCase):
    def load_agent(self, values):
        with (
            patch.dict(os.environ, values, clear=True),
            patch("dotenv.load_dotenv"),
            patch("agent_framework.Agent"),
            patch("agent_framework.ag_ui.add_agent_framework_fastapi_endpoint"),
            patch("agent_framework.openai.OpenAIChatCompletionClient") as client,
            patch("agent_framework.foundry.FoundryChatClient") as foundry,
            patch("azure.identity.AzureCliCredential") as credential,
        ):
            runpy.run_path(str(Path(__file__).resolve().parents[1] / "agent" / "main.py"))
        return client, foundry, credential

    def test_foundry_uses_cli_identity_even_with_a_stale_key(self):
        client, foundry, credential = self.load_agent({
            "LLM_MODE": "foundry",
            "FOUNDRY_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/demo",
            "FOUNDRY_MODEL": "model-demo",
            "AZURE_OPENAI_API_KEY": "unit-test-only",
        })
        credential.assert_called_once_with()
        foundry.assert_called_once_with(
            project_endpoint="https://demo.services.ai.azure.com/api/projects/demo",
            model="model-demo",
            credential=credential.return_value,
        )
        client.assert_not_called()

    def test_azure_uses_cli_identity_even_with_a_stale_key(self):
        client, foundry, credential = self.load_agent({
            "LLM_MODE": "azure",
            "AZURE_OPENAI_ENDPOINT": "https://demo.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "model-demo",
            "AZURE_OPENAI_API_KEY": "unit-test-only",
        })
        credential.assert_called_once_with()
        self.assertEqual(client.call_args.kwargs["credential"], credential.return_value)
        self.assertNotIn("api_key", client.call_args.kwargs)
        foundry.assert_not_called()


if __name__ == "__main__":
    unittest.main()
