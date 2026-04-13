import unittest

from mathagent.orchestrator import Orchestrator
from mathagent.reporting import required_report_titles
from mathagent.tools import ToolRegistry
from mathagent.verification.checkers import (
    build_report_sources,
    build_verification_findings,
    build_verification_summary,
)


class VerificationSummaryTest(unittest.TestCase):
    def test_verification_summary_tracks_report_checks(self) -> None:
        state = Orchestrator(
            tools=ToolRegistry.with_defaults(out_dir="tests/verification_outputs"),
        ).run("Problem 1: forecast demand for 3 days using values 5 7 9 11.")

        summary = build_verification_summary(state)
        sources = build_report_sources(state)

        self.assertIn("report_checks", summary)
        self.assertIn("section_count", summary["report_checks"])
        self.assertIn("results", sources)
        self.assertIn("referenced_evidence_count", sources["results"])

    def test_verification_findings_flag_missing_sections_and_uncited_subproblems(self) -> None:
        state = Orchestrator(
            tools=ToolRegistry.with_defaults(out_dir="tests/verification_outputs"),
        ).run("Problem 1: forecast demand for 3 days using values 5 7 9 11.")

        state.report_md = required_report_titles()[0] + "\nOnly abstract content."
        summary = build_verification_summary(state)
        sources = build_report_sources(state)
        findings = build_verification_findings(state, summary, sources)

        messages = [item["message"] for item in findings]
        self.assertTrue(any("Missing required report section" in message for message in messages))
        self.assertTrue(any("does not consistently cite evidence" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
