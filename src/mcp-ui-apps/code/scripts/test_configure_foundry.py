from pathlib import Path
import tempfile
import unittest

from dotenv import dotenv_values

from configure_foundry import configure


class ConfigureFoundryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = Path(self.directory.name) / ".env"
        self.values = {
            "LLM_MODE": "azure",
            "AZURE_OPENAI_ENDPOINT": "https://demo.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "model-demo",
        }

    def test_updates_existing_configuration_without_losing_other_settings(self):
        self.env.write_text(
            "# Keep this comment\nLOG_LEVEL=DEBUG\nLLM_MODE=fake\n"
            "export AZURE_OPENAI_DEPLOYMENT=old\nAZURE_OPENAI_DEPLOYMENT=duplicate\n"
            "AZURE_OPENAI_API_KEY=unit-test-only\n",
            encoding="utf-8",
        )
        configure(self.env, self.values)
        configure(self.env, self.values)
        parsed = dotenv_values(self.env)
        self.assertEqual(parsed["LOG_LEVEL"], "DEBUG")
        self.assertIn("# Keep this comment", self.env.read_text(encoding="utf-8"))
        for key, value in self.values.items():
            self.assertEqual(parsed[key], value)
        self.assertNotIn("duplicate", self.env.read_text(encoding="utf-8"))
        self.assertNotIn("AZURE_OPENAI_API_KEY", parsed)

    def test_seeds_missing_env_from_example(self):
        self.env.with_name(".env.example").write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
        configure(self.env, self.values)
        self.assertEqual(dotenv_values(self.env)["LOG_LEVEL"], "INFO")
        self.assertEqual(dotenv_values(self.env)["AZURE_OPENAI_DEPLOYMENT"], "model-demo")

    def test_invalid_output_does_not_modify_existing_file(self):
        original = "LLM_MODE=fake\n"
        self.env.write_text(original, encoding="utf-8")
        for key, value in [
            ("LLM_MODE", "foundry"),
            ("AZURE_OPENAI_ENDPOINT", "https://<your-resource>.openai.azure.com"),
            ("AZURE_OPENAI_ENDPOINT", "http://example.com"),
            ("AZURE_OPENAI_DEPLOYMENT", "model\nLOG_LEVEL=DEBUG"),
            ("AZURE_OPENAI_DEPLOYMENT", ""),
        ]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    configure(self.env, {**self.values, key: value})
                self.assertEqual(self.env.read_text(encoding="utf-8"), original)

    def test_missing_output_does_not_create_env(self):
        with self.assertRaises(KeyError):
            configure(self.env, {"LLM_MODE": "azure"})
        self.assertFalse(self.env.exists())


if __name__ == "__main__":
    unittest.main()
