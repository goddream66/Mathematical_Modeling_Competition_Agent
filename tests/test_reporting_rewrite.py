import unittest

from mathagent.reporting_rewrite import stabilize_report_markdown
from mathagent.state import SolverRun, SubProblem, TaskState


class ReportingRewriteTest(unittest.TestCase):
    def test_stabilize_report_marks_provisional_mismatch_and_review_section(self) -> None:
        subproblem = SubProblem(title="Problem 2", text="Locate points from measurements.")
        subproblem.analysis.objective = "Estimate locations from geometry constraints."
        subproblem.analysis.chosen_method = "logistic_regression"
        subproblem.analysis.constraints = ["pending_constraint"]
        state = TaskState(
            problem_text="Problem 2: estimate locations from geometry measurements.",
            subproblems=[subproblem],
            solver_runs=[
                SolverRun(
                    subproblem_title="Problem 2",
                    success=True,
                    summary="Recovered after timeout.",
                    code="print('ok')",
                    stderr="Recovered from CODING generation failure: timeout\nRetried with fallback solver.",
                    schema_valid=True,
                    structured_result={
                        "subproblem_title": "Problem 2",
                        "status": "partial",
                        "method": "geometry_localization_template",
                        "result_summary": "Generated a diagnostic localization validation bundle.",
                        "constraints": ["pending_constraint"],
                        "evidence": ["template_used=geometry_localization_template"],
                        "numeric_results": {"point_count": 0, "measurement_count": 0},
                        "figure_titles": ["Problem 2: localization residual check"],
                        "final_verdict": "needs_review",
                    },
                )
            ],
            results={
                "status": "partially_solved",
                "review_findings": [
                    {
                        "severity": "high",
                        "message": "Problem 2 executed method does not match modeling method.",
                        "suggestion": "Explain the method switch.",
                    }
                ],
            },
        )

        report = stabilize_report_markdown("# 摘要\n初稿。", state)

        self.assertIn("暂定结果", report)
        self.assertIn("方法与实际执行方法不一致", report)
        self.assertIn("审稿提示", report)
        self.assertIn("约束仍不完整", report)
        self.assertNotIn("pending_constraint", report)
        self.assertNotIn("## Structured Results Alignment", report)


if __name__ == "__main__":
    unittest.main()
