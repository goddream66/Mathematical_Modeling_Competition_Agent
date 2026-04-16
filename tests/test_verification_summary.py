import unittest

from mathagent.orchestrator import Orchestrator
from mathagent.reporting import required_report_titles
from mathagent.state import SolverRun, SubProblem, TaskState
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

    def test_verification_findings_escalate_results_without_evidence(self) -> None:
        subproblem = SubProblem(title="Problem 1", text="Produce a structured result.")
        subproblem.analysis.objective = "Produce a scored result."
        subproblem.analysis.constraints = ["Evidence must be cited."]
        subproblem.analysis.chosen_method = "demo_method"
        state = TaskState(
            problem_text="Problem 1: produce a structured result.",
            subproblems=[subproblem],
            solver_runs=[
                SolverRun(
                    subproblem_title="Problem 1",
                    success=True,
                    summary="ok",
                    code="print('ok')",
                    schema_valid=True,
                    structured_result={
                        "subproblem_title": "Problem 1",
                        "status": "ok",
                        "method": "demo_method",
                        "objective": "Produce a scored result.",
                        "assumptions": ["demo"],
                        "constraints": ["Evidence must be cited."],
                        "result_summary": "Generated a structured result.",
                        "evidence": ["marker=demo"],
                        "numeric_results": {"score": 1},
                        "figure_titles": [],
                        "artifacts": ["result.json"],
                        "next_steps": [],
                    },
                )
            ],
            report_md="\n".join(
                [
                    "# 摘要",
                    "摘要内容。",
                    "",
                    "# 问题重述",
                    "问题重述。",
                    "",
                    "# 子问题分析与方法选择",
                    "## Problem 1",
                    "分析内容。",
                    "",
                    "# 模型假设与符号说明",
                    "建模内容。",
                    "",
                    "# 求解与实验",
                    "## Problem 1",
                    "- method: demo_method",
                    "",
                    "# 结果与分析",
                    "## Problem 1",
                    "这里只给出笼统结论，没有引用任何证据。",
                    "",
                    "# 结论与后续工作",
                    "结论。",
                ]
            ),
        )

        summary = build_verification_summary(state)
        sources = build_report_sources(state)
        findings = build_verification_findings(state, summary, sources)

        self.assertTrue(
            any(
                item["message"] == "The results section does not explicitly cite solver evidence markers."
                and item["severity"] == "high"
                for item in findings
            )
        )


if __name__ == "__main__":
    unittest.main()
