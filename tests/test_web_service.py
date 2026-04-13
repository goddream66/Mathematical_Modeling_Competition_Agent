import unittest
from pathlib import Path
from uuid import uuid4

from mathagent.web import WebSessionService


class WebSessionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root_dir = Path("tests/web_outputs")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root_dir / f"sessions_{uuid4().hex}.db"
        self.service = WebSessionService(root_dir=self.root_dir, db_path=self.db_path)
        self.session = self.service.create_session()

    def test_run_session_with_messages_and_sections(self) -> None:
        self.service.add_message(
            self.session["session_id"],
            "Problem 1: forecast demand for 3 days using values 5 7 9 11.",
        )
        self.service.set_report_sections(self.session["session_id"], ["abstract", "results"])
        payload = self.service.run_session(self.session["session_id"])

        self.assertTrue(payload["report_ready"])
        self.assertIn("# 摘要", payload["report"]["selected_report_md"])
        self.assertIn("# 结果与分析", payload["report"]["selected_report_md"])
        self.assertNotIn("# 求解与实验", payload["report"]["selected_report_md"])

    def test_upload_data_file_and_run(self) -> None:
        csv_path = Path("tests/fixtures/forecast_series.csv")
        self.service.add_message(
            self.session["session_id"],
            "Problem 1: forecast demand for the next 3 days.",
        )
        self.service.upload_files(
            self.session["session_id"],
            role="data",
            files=[(csv_path.name, csv_path.read_bytes())],
        )
        payload = self.service.run_session(self.session["session_id"])

        latest_state = payload["latest_state"]
        self.assertIsNotNone(latest_state)
        self.assertEqual(latest_state["solver_run_count"], 1)
        self.assertEqual(payload["data_files"][0]["name"], "forecast_series.csv")

    def test_session_persistence_across_service_instances(self) -> None:
        self.service.add_message(
            self.session["session_id"],
            "Problem 1: optimize profit under budget 100.",
        )

        reloaded = WebSessionService(root_dir=self.root_dir, db_path=self.db_path)
        sessions = reloaded.list_sessions()

        self.assertTrue(sessions)
        self.assertEqual(sessions[0]["session_id"], self.session["session_id"])
        self.assertEqual(sessions[0]["messages"][0], "Problem 1: optimize profit under budget 100.")

    def test_run_session_records_verification_and_report_sources(self) -> None:
        self.service.add_message(
            self.session["session_id"],
            "Problem 1: forecast demand for 3 days using values 5 7 9 11.",
        )
        payload = self.service.run_session(self.session["session_id"])

        latest_state = payload["latest_state"]
        assert latest_state is not None
        verification_summary = latest_state["results"]["verification_summary"]
        report_sources = latest_state["results"]["report_sources"]

        self.assertIn("overall_verdict", verification_summary)
        self.assertIn("abstract", report_sources)
        self.assertIn("present", report_sources["abstract"])


if __name__ == "__main__":
    unittest.main()
