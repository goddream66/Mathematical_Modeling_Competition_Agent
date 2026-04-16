import json
import unittest
from unittest.mock import patch

from mathagent.agents import specialists_v3 as spec
from mathagent.state import SubProblem, TaskState
from mathagent.tools import ToolRegistry


BAD_CODE = "items = []\nitems.append(value=1)\n"
FALLBACK_CODE = "print('fallback solver')\n"


class FakeLLM:
    def __init__(self, response: str) -> None:
        self._response = response

    def chat(self, messages, temperature: float = 0.0) -> str:  # noqa: ANN001
        return self._response


class FakePythonExecTool:
    name = "python_exec"
    description = "Fake python execution tool for tests"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, input: dict) -> dict:  # noqa: A002
        self.calls.append(input)

        if input["code"] == FALLBACK_CODE:
            payload = {
                "subproblem_title": "Problem 1",
                "status": "ok",
                "method": "fallback_method",
                "objective": "Produce a stable structured result.",
                "assumptions": ["Fallback template is allowed."],
                "constraints": ["Use template output when generated code fails."],
                "result_summary": "Recovered with fallback solver.",
                "evidence": [],
                "numeric_results": {"forecast_value": 14.0, "backtest_mae": 0.8},
                "figure_titles": ["Recovered Figure"],
                "artifacts": ["result.json"],
                "next_steps": ["Replace fallback solver with domain logic."],
            }
            return {
                "success": True,
                "run_dir": "",
                "artifacts": [],
                "stdout": json.dumps(payload, ensure_ascii=False),
                "stderr": "",
            }

        return {
            "success": False,
            "run_dir": "",
            "artifacts": [],
            "stdout": "",
            "stderr": "TypeError: list.append() takes no keyword arguments",
        }


class StructuredPythonExecTool:
    name = "python_exec"
    description = "Structured python execution tool for adequacy tests"

    def __init__(self, primary_payload: dict, fallback_payload: dict | None) -> None:
        self.primary_payload = primary_payload
        self.fallback_payload = fallback_payload
        self.calls: list[dict] = []

    def run(self, input: dict) -> dict:  # noqa: A002
        self.calls.append(input)
        payload = self.fallback_payload if input["code"] == FALLBACK_CODE else self.primary_payload
        if payload is None:
            return {
                "success": False,
                "run_dir": "",
                "artifacts": [],
                "stdout": "",
                "stderr": "fallback execution failed",
            }
        return {
            "success": True,
            "run_dir": "",
            "artifacts": [],
            "stdout": json.dumps(payload, ensure_ascii=False),
            "stderr": "",
        }


class DummyMemory:
    def set_shared(self, key: str, value: str) -> None:  # noqa: ARG002
        return None

    def set_shared_json(self, key: str, value) -> None:  # noqa: ANN001, ARG002
        return None

    def set_agent(self, agent: str, key: str, value: str) -> None:  # noqa: ARG002
        return None

    def set_agent_json(self, agent: str, key: str, value) -> None:  # noqa: ANN001, ARG002
        return None

    def append_event(self, scope: str, agent: str, type: str, payload) -> None:  # noqa: ANN001, A003, ARG002
        return None


def _build_state(
    text: str = "Forecast demand from numeric clues 10 12 13 16.",
    *,
    chosen_method: str = "time_series",
    objective: str = "Estimate the next value.",
    assumptions: list[str] | None = None,
    constraints: list[str] | None = None,
) -> TaskState:
    subproblem = SubProblem(title="Problem 1", text=text)
    subproblem.analysis.chosen_method = chosen_method
    subproblem.analysis.objective = objective
    subproblem.analysis.assumptions = assumptions or ["Data trend is smooth."]
    subproblem.analysis.constraints = constraints or ["Only baseline data is available."]
    return TaskState(problem_text=subproblem.text, subproblems=[subproblem], stage="solve")


class CodingResilienceTest(unittest.TestCase):
    def test_validate_result_schema_synthesizes_evidence(self) -> None:
        payload = {
            "subproblem_title": "Problem 1",
            "status": "ok",
            "method": "demo_method",
            "objective": "Return structured results.",
            "assumptions": ["Assume baseline inputs are valid."],
            "constraints": ["Keep the schema stable."],
            "result_summary": "Structured results were generated.",
            "evidence": [],
            "numeric_results": {"rmse": 0.5},
            "figure_titles": ["Figure 1"],
            "artifacts": ["result.json", "chart.svg"],
            "next_steps": ["Add stronger validation."],
        }

        valid, normalized, error = spec._validate_result_schema(payload, "Problem 1")

        self.assertTrue(valid, error)
        self.assertTrue(normalized["evidence"])
        self.assertIn("auto_evidence=synthesized_from_available_outputs", normalized["evidence"])
        self.assertIn("numeric_result_keys=rmse", normalized["evidence"])

    def test_build_llm_solver_falls_back_when_generated_code_is_invalid(self) -> None:
        state = _build_state()
        subproblem = state.subproblems[0]
        llm_response = json.dumps(
            {
                "summary": "Generated invalid code.",
                "code": "```python\nif True print('broken')\n```",
            },
            ensure_ascii=False,
        )

        with (
            patch.object(spec, "load_llm_config", return_value=object()),
            patch.object(spec, "build_llm", return_value=FakeLLM(llm_response)),
            patch.object(spec, "render_prompt", return_value="prompt"),
        ):
            summary, code = spec._build_llm_solver(state, subproblem, 1)

        self.assertIn("Fallback was used because generated code had invalid syntax", summary)
        self.assertIn("template_used=", code)
        self.assertNotIn("if True print('broken')", code)

    def test_coding_agent_retries_with_fallback_after_runtime_error(self) -> None:
        state = _build_state()
        tool = FakePythonExecTool()
        tools = ToolRegistry.empty()
        tools.register(tool)
        memory = DummyMemory()

        with (
            patch.object(spec, "_build_llm_solver", return_value=("Generated solver.", BAD_CODE)),
            patch.object(spec, "_build_fallback_solver_code", return_value=("Fallback solver.", FALLBACK_CODE)),
            patch.object(spec.SolveSkill, "run", lambda self, state, tools: state),
        ):
            updated = spec.CodingAgent().run(state, tools, memory)

        self.assertEqual(len(tool.calls), 2)
        self.assertEqual(tool.calls[1]["filename"], "solver_1_fallback.py")
        self.assertEqual(updated.results["status"], "solved")
        self.assertEqual(updated.solver_runs[0].code, FALLBACK_CODE)
        self.assertTrue(updated.solver_runs[0].schema_valid)
        self.assertTrue(updated.solver_runs[0].success)
        self.assertIn("auto_evidence=synthesized_from_available_outputs", updated.solver_runs[0].structured_result["evidence"])
        self.assertTrue(updated.solver_runs[0].structured_result["verification_checks"])
        self.assertEqual(updated.solver_runs[0].structured_result["final_verdict"], "validated")
        self.assertIn("plot_code_hint", updated.solver_runs[0].structured_result)

    def test_coding_agent_retries_with_fallback_after_weak_forecast_result(self) -> None:
        state = _build_state()
        primary_payload = {
            "subproblem_title": "Problem 1",
            "status": "ok",
            "method": "time_series",
            "objective": "Estimate the next value.",
            "assumptions": ["Data trend is smooth."],
            "constraints": ["Only baseline data is available."],
            "result_summary": "Generated a minimal structured forecast result.",
            "evidence": ["generated_solver=llm"],
            "numeric_results": {"historical_point_count": 4},
            "figure_titles": ["Initial Forecast Figure"],
            "artifacts": ["result.json"],
            "next_steps": [],
        }
        fallback_payload = {
            "subproblem_title": "Problem 1",
            "status": "ok",
            "method": "fallback_method",
            "objective": "Produce forecast metrics.",
            "assumptions": ["Fallback template is allowed."],
            "constraints": ["Use template output when generated metrics are weak."],
            "result_summary": "Recovered a forecast result with explicit metrics.",
            "evidence": ["template_used=forecast_validation_template"],
            "numeric_results": {"naive_reference_forecast": 17.5, "backtest_mae": 1.2},
            "figure_titles": ["Recovered Forecast Figure", "Recovered Forecast Residuals"],
            "artifacts": ["result.json"],
            "next_steps": ["Replace the baseline forecast with a domain-specific model."],
        }
        tool = StructuredPythonExecTool(primary_payload, fallback_payload)
        tools = ToolRegistry.empty()
        tools.register(tool)
        memory = DummyMemory()

        with (
            patch.object(spec, "_build_llm_solver", return_value=("Generated solver.", "print('ok')\n")),
            patch.object(spec, "_build_fallback_solver_code", return_value=("Fallback solver.", FALLBACK_CODE)),
            patch.object(spec.SolveSkill, "run", lambda self, state, tools: state),
        ):
            updated = spec.CodingAgent().run(state, tools, memory)

        self.assertEqual(len(tool.calls), 2)
        self.assertEqual(tool.calls[1]["filename"], "solver_1_fallback.py")
        self.assertEqual(updated.solver_runs[0].code, FALLBACK_CODE)
        self.assertEqual(updated.solver_runs[0].structured_result["numeric_results"]["naive_reference_forecast"], 17.5)
        self.assertEqual(updated.results["status"], "solved")
        self.assertIn("solver adequacy checks failed", updated.solver_runs[0].summary)
        self.assertIn("backtest_mae", updated.solver_runs[0].structured_result["error_metrics"])

    def test_coding_agent_downgrades_weak_result_when_fallback_does_not_help(self) -> None:
        state = _build_state(
            "Optimize cost under budget 100 with candidate costs 20 35 40.",
            chosen_method="linear_programming",
            objective="Minimize cost under a budget constraint.",
            assumptions=["Costs are deterministic."],
            constraints=["Budget cannot exceed 100."],
        )
        primary_payload = {
            "subproblem_title": "Problem 1",
            "status": "ok",
            "method": "linear_programming",
            "objective": "Minimize cost under a budget constraint.",
            "assumptions": ["Costs are deterministic."],
            "constraints": ["Budget cannot exceed 100."],
            "result_summary": "Generated a minimal optimization result.",
            "evidence": ["generated_solver=llm"],
            "numeric_results": {"item_count": 3},
            "figure_titles": ["Optimization Figure"],
            "artifacts": ["result.json"],
            "next_steps": [],
        }
        tool = StructuredPythonExecTool(primary_payload, None)
        tools = ToolRegistry.empty()
        tools.register(tool)
        memory = DummyMemory()

        with (
            patch.object(spec, "_build_llm_solver", return_value=("Generated solver.", "print('ok')\n")),
            patch.object(spec, "_build_fallback_solver_code", return_value=("Fallback solver.", FALLBACK_CODE)),
            patch.object(spec.SolveSkill, "run", lambda self, state, tools: state),
        ):
            updated = spec.CodingAgent().run(state, tools, memory)

        self.assertEqual(len(tool.calls), 2)
        self.assertEqual(updated.solver_runs[0].code, "print('ok')\n")
        self.assertEqual(updated.solver_runs[0].structured_result["status"], "partial")
        self.assertIn("auto_check=repair_needed", updated.solver_runs[0].structured_result["evidence"])
        self.assertTrue(updated.solver_runs[0].structured_result["next_steps"])
        self.assertEqual(updated.results["status"], "partially_solved")
        self.assertIn("Auto-check flagged incomplete solver result", updated.solver_runs[0].stderr)
        self.assertEqual(updated.solver_runs[0].structured_result["final_verdict"], "needs_review")
        self.assertTrue(updated.solver_runs[0].structured_result["suspicious_points"])


if __name__ == "__main__":
    unittest.main()
