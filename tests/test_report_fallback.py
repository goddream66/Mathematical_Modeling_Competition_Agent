import unittest

from mathagent.orchestrator import Orchestrator
from mathagent.tools import ToolRegistry


class ReportFallbackTest(unittest.TestCase):
    def test_report_mentions_result_summary_and_figure_titles(self) -> None:
        state = Orchestrator(
            tools=ToolRegistry.with_defaults(out_dir="tests/report_outputs"),
        ).run("Problem 1: forecast demand for 3 days using values 5 7 9 11.")

        assert state.report_md is not None
        self.assertIn("# 结果与分析", state.report_md)
        self.assertIn("naive_reference_forecast", state.report_md)
        self.assertIn("图表标题", state.report_md)
        self.assertNotIn("## Structured Results Alignment", state.report_md)


if __name__ == "__main__":
    unittest.main()

