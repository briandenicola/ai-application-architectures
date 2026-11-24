import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import demo, telemetry


class TelemetryTests(unittest.TestCase):
    def config(self):
        return {
            "subscription_id": "synthetic-subscription",
            "application_insights_id": "/subscriptions/s/components/insights",
            "application_insights_app_id": "application",
            "project_endpoint": "https://project.example.com",
            "agent_name": "handbook",
        }

    def result(self, rows=None):
        return {
            "tables": [
                {
                    "name": "PrimaryResult",
                    "columns": [{"name": "operation_Id"}, {"name": "name"}],
                    "rows": rows or [],
                }
            ]
        }

    def test_query_is_exact_response_scoped_then_expands_only_its_operations(self):
        query = telemetry.trace_query("resp_synthetic")
        self.assertIn('customDimensions["gen_ai.response.id"]) == "resp_synthetic"', query)
        self.assertIn("operation_Id in (operations)", query)
        self.assertIn("timestamp > ago(24h)", query)
        for invalid in ("../escape", 'resp_" | take 1', "", None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                telemetry.trace_query(invalid)

    def test_partial_missing_or_malformed_query_data_is_not_success(self):
        for result in (
            {"error": {"code": "PartialError"}, **self.result([["trace", "span"]])},
            {},
            {"tables": []},
            {"tables": [{"name": "PrimaryResult", "columns": [{"name": "a"}], "rows": [[1, 2]]}]},
        ):
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                telemetry.query_rows(result)

    def test_waits_for_current_response_and_saves_observed_records(self):
        client = Mock()
        client.request.side_effect = [self.result(), self.result([["trace-current", "agent"]])]
        record = {"response": {"id": "resp_synthetic", "output": [{"type": "mcp_call"}]}}
        clock = [0]

        def advance(seconds):
            clock[0] += seconds

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(telemetry.os.environ, {"TRACE_WAIT_SECONDS": "120"}, clear=True),
            patch.object(telemetry.time, "sleep", side_effect=advance) as sleep,
            patch.object(telemetry.time, "monotonic", side_effect=lambda: clock[0]),
        ):
            telemetry.report(client, self.config(), "resp_synthetic", directory, record)
            saved = json.loads(
                (Path(directory) / ".artifacts/traces/resp_synthetic.json").read_text()
            )
        self.assertEqual(saved["telemetry"]["status"], "observed")
        self.assertEqual(saved["telemetry"]["records"][0]["operation_Id"], "trace-current")
        self.assertEqual(saved["response"], record["response"])
        sleep.assert_called_once_with(10)
        request = client.request.call_args
        self.assertEqual(request.args[2], telemetry.AUDIENCE)
        self.assertTrue(request.args[1].endswith("/apps/application/query"))
        self.assertEqual(request.args[3]["timespan"], "PT24H")
        self.assertLessEqual(request.kwargs["timeout"], 30)

    def test_timeout_remains_pending_and_retry_preserves_original_response(self):
        client = Mock()
        client.request.return_value = self.result()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(telemetry.os.environ, {"TRACE_WAIT_SECONDS": "0"}, clear=True),
            patch.object(demo.sys, "stdout", new_callable=io.StringIO) as output,
        ):
            telemetry.report(
                client,
                self.config(),
                "resp_synthetic",
                directory,
                {"response": {"id": "resp_synthetic"}},
            )
            path = Path(directory) / ".artifacts/traces/resp_synthetic.json"
            self.assertEqual(json.loads(path.read_text())["telemetry"]["status"], "pending")
            self.assertIn("task traces -- resp_synthetic", output.getvalue())
            client.request.return_value = self.result([["trace", "agent"]])
            telemetry.report(client, self.config(), "resp_synthetic", directory)
            saved = json.loads(path.read_text())
        self.assertEqual(saved["response"]["id"], "resp_synthetic")
        self.assertEqual(saved["telemetry"]["status"], "observed")

    def test_positive_wait_stops_at_deadline_without_an_extra_query(self):
        client = Mock()
        client.request.return_value = self.result()
        clock = [0]

        def advance(seconds):
            clock[0] += seconds

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(telemetry.os.environ, {"TRACE_WAIT_SECONDS": "120"}, clear=True),
            patch.object(telemetry.time, "sleep", side_effect=advance),
            patch.object(telemetry.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(demo.sys, "stdout", new_callable=io.StringIO),
        ):
            telemetry.report(client, self.config(), "resp_synthetic", directory)
            saved = json.loads(
                (Path(directory) / ".artifacts/traces/resp_synthetic.json").read_text()
            )
        self.assertEqual(clock[0], 120)
        self.assertEqual(client.request.call_count, 12)
        self.assertEqual(saved["telemetry"]["status"], "pending")

    def test_query_failure_is_recorded_and_propagated_not_treated_as_pending(self):
        client = Mock()
        client.request.side_effect = demo.ServiceError(403, "POST", "https://query", "Denied")
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(demo.ServiceError, "403"),
        ):
            try:
                telemetry.report(client, self.config(), "resp_synthetic", directory)
            finally:
                saved = json.loads(
                    (Path(directory) / ".artifacts/traces/resp_synthetic.json").read_text()
                )
                self.assertEqual(saved["telemetry"]["status"], "error")
                self.assertNotIn("records", saved["telemetry"])

    def test_legacy_config_and_invalid_wait_fail_before_agent_call(self):
        missing_application = self.config()
        missing_application.pop("application_insights_app_id")
        missing_resource = self.config()
        missing_resource.pop("application_insights_id")
        for config, wait in [
            (missing_application, "120"),
            (missing_resource, "120"),
            (self.config(), "-1"),
            (self.config(), "invalid"),
        ]:
            client = Mock()
            client.request.side_effect = RuntimeError("An agent call must not happen.")
            with (
                self.subTest(config=config, wait=wait),
                patch.dict(telemetry.os.environ, {"TRACE_WAIT_SECONDS": wait}, clear=True),
                self.assertRaises((RuntimeError, ValueError)),
            ):
                demo.ask(client, config, "Question")
            client.request.assert_not_called()

    def test_ask_prints_details_and_collects_traces_even_on_validation_failure(self):
        response = {
            "id": "resp_synthetic",
            "status": "completed",
            "model": "demo-model",
            "usage": {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20},
            "output": [
                {
                    "type": "mcp_call",
                    "name": "knowledge_base_retrieve",
                    "id": "call-1",
                    "status": "completed",
                    "arguments": '{"query":"leave"}',
                    "output": "Synthetic retrieval result",
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "20 days [leave-policy.md]."}],
                },
            ],
        }
        for valid in (True, False):
            value = copy.deepcopy(response)
            if not valid:
                value["output"][0]["error"] = {"message": "Denied"}
            client = Mock()
            client.request.return_value = value
            with (
                self.subTest(valid=valid),
                patch.object(demo.telemetry, "report") as report,
                patch.object(demo.sys, "stdout", new_callable=io.StringIO) as output,
            ):
                if valid:
                    demo.ask(client, self.config(), "Question")
                else:
                    with self.assertRaisesRegex(RuntimeError, "Denied"):
                        demo.ask(client, self.config(), "Question")
            report.assert_called_once()
            self.assertEqual(report.call_args.args[2], "resp_synthetic")
            self.assertEqual(report.call_args.args[4]["response"], value)
            self.assertIn("MCP: knowledge_base_retrieve", output.getvalue())
            self.assertIn('"total_tokens": 20', output.getvalue())
            self.assertIn("Output: Synthetic retrieval result", output.getvalue())

    def test_agent_failure_is_not_masked_by_a_second_telemetry_failure(self):
        client = Mock()
        client.request.return_value = {
            "id": "resp_synthetic",
            "status": "failed",
            "error": {"message": "Agent failed"},
        }
        with (
            patch.object(demo.telemetry, "report", side_effect=RuntimeError("query blocked")),
            patch.object(demo.sys, "stdout", new_callable=io.StringIO),
            patch.object(demo.sys, "stderr", new_callable=io.StringIO),
            self.assertRaisesRegex(RuntimeError, r"(?s)Agent failed.*query blocked"),
        ):
            demo.ask(client, self.config(), "Question")

    def test_missing_usage_is_not_fabricated_and_trace_command_does_not_invoke_agent(self):
        summary = telemetry.response_summary({"id": "resp_synthetic"}, 1.25)
        self.assertIsNone(summary["usage"])
        with (
            patch.object(demo.sys, "argv", ["demo", "traces"]),
            patch.dict(demo.os.environ, {"DEMO_RESPONSE_ID": "resp_synthetic"}),
            patch.object(demo, "configuration", return_value=self.config()),
            patch.object(demo.telemetry, "report") as report,
            patch.object(demo, "ask") as ask,
        ):
            self.assertEqual(demo.main(), 0)
        report.assert_called_once()
        ask.assert_not_called()
