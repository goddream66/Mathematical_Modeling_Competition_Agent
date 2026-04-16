import unittest

from mathagent.reviewing import (
    build_structural_review_findings,
    has_blocking_review_findings,
)
from mathagent.state import SolverRun, SubProblem, TaskState


class ReviewingTest(unittest.TestCase):
    def test_structural_review_flags_thin_modeling_and_solver_outputs(self) -> None:
        subproblem = SubProblem(title="Problem 1", text="Forecast demand.")
        subproblem.analysis.objective = "Predict next demand value."
        subproblem.analysis.chosen_method = "time_series"
        subproblem.analysis.constraints = ["Use available observations only."]
        subproblem.analysis.confidence = 0.3

        state = TaskState(
            problem_text="Problem 1: Forecast demand.",
            subproblems=[subproblem],
            solver_runs=[
                SolverRun(
                    subproblem_title="Problem 1",
                    success=True,
                    summary="ok",
                    code="print('ok')",
                    schema_valid=True,
                    artifacts=["plot.svg", "result.json"],
                    structured_result={
                        "subproblem_title": "Problem 1",
                        "status": "ok",
                        "method": "time_series",
                        "objective": "Predict next demand value.",
                        "assumptions": ["Trend is smooth."],
                        "constraints": ["Use available observations only."],
                        "result_summary": "Solved successfully.",
                        "evidence": ["marker=forecast"],
                        "numeric_results": {},
                        "figure_titles": [],
                        "artifacts": ["plot.svg", "result.json"],
                        "next_steps": [],
                    },
                )
            ],
            report_md="# Abstract\nNo figure citation here.",
        )

        findings = build_structural_review_findings(state)
        messages = [item["message"] for item in findings]

        self.assertTrue(any("formulation steps" in message for message in messages))
        self.assertTrue(any("missing explicit modeling assumptions" in message for message in messages))
        self.assertTrue(any("low modeling confidence" in message for message in messages))
        self.assertTrue(any("does not expose any numeric results" in message for message in messages))
        self.assertTrue(any("without figure_titles metadata" in message for message in messages))
        self.assertTrue(any("missing detailed subsection headings" in message for message in messages))

    def test_structural_review_flags_missing_figure_title_in_report_and_missing_next_steps(self) -> None:
        subproblem = SubProblem(title="Problem 2", text="Optimize allocation.")
        subproblem.analysis.objective = "Maximize value."
        subproblem.analysis.chosen_method = "optimization"
        subproblem.analysis.constraints = ["Budget <= 100."]
        subproblem.analysis.assumptions = ["Linear utility."]
        subproblem.analysis.formulation_steps = ["Define variables.", "Write objective."]

        state = TaskState(
            problem_text="Problem 2: Optimize allocation.",
            subproblems=[subproblem],
            solver_runs=[
                SolverRun(
                    subproblem_title="Problem 2",
                    success=False,
                    summary="partial",
                    code="print('partial')",
                    schema_valid=True,
                    artifacts=["allocation.svg", "result.json"],
                    structured_result={
                        "subproblem_title": "Problem 2",
                        "status": "partial",
                        "method": "optimization",
                        "objective": "Maximize value.",
                        "assumptions": ["Linear utility."],
                        "constraints": ["Budget <= 100."],
                        "result_summary": "Need stronger constraints.",
                        "evidence": ["marker=allocation"],
                        "numeric_results": {"score": 1},
                        "figure_titles": ["Allocation Summary Figure"],
                        "artifacts": ["allocation.svg", "result.json"],
                        "next_steps": [],
                    },
                )
            ],
            report_md="# Results\nPartial discussion without the chart title.",
        )

        findings = build_structural_review_findings(state)
        messages = [item["message"] for item in findings]

        self.assertTrue(any("does not provide next steps" in message for message in messages))
        self.assertTrue(any("does not explicitly cite figure title 'Allocation Summary Figure'" in message for message in messages))

    def test_high_severity_findings_block_final_review(self) -> None:
        findings = [
            {
                "severity": "high",
                "area": "coding",
                "message": "Critical issue.",
                "suggestion": "Fix it.",
            }
        ]

        self.assertTrue(has_blocking_review_findings(findings))

    def test_structural_review_flags_method_result_mismatch_for_forecast_tasks(self) -> None:
        subproblem = SubProblem(title="Problem 3", text="Forecast next-week demand.")
        subproblem.analysis.objective = "Forecast demand."
        subproblem.analysis.chosen_method = "time_series_forecast"
        subproblem.analysis.constraints = ["Use only observed values."]
        subproblem.analysis.assumptions = ["Demand is smooth."]
        subproblem.analysis.formulation_steps = ["Collect the series.", "Fit a baseline model."]
        subproblem.analysis.task_types = ["forecast"]

        state = TaskState(
            problem_text="Problem 3: Forecast next-week demand.",
            subproblems=[subproblem],
            solver_runs=[
                SolverRun(
                    subproblem_title="Problem 3",
                    success=True,
                    summary="ok",
                    code="print('ok')",
                    schema_valid=True,
                    structured_result={
                        "subproblem_title": "Problem 3",
                        "status": "ok",
                        "method": "time_series_forecast",
                        "objective": "Forecast demand.",
                        "assumptions": ["Demand is smooth."],
                        "constraints": ["Use only observed values."],
                        "result_summary": "A result was generated.",
                        "evidence": ["method_marker=time_series_forecast"],
                        "numeric_results": {"sample_count": 5},
                        "figure_titles": [],
                        "artifacts": ["result.json"],
                        "next_steps": [],
                    },
                )
            ],
        )

        findings = build_structural_review_findings(state)
        self.assertTrue(
            any("forecasting task" in item["message"] for item in findings),
            findings,
        )


if __name__ == "__main__":
    unittest.main()
