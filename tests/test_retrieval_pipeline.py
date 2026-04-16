import json
import unittest

from mathagent.agents.specialists_v3 import _build_solver_context
from mathagent.orchestrator import _EphemeralMemory
from mathagent.retrieval import (
    RetrievalChunk,
    StaticRetriever,
    format_retrieval_context,
    select_retrieval_chunks,
)
from mathagent.state import SubProblem, TaskState
from mathagent.tools import ToolRegistry
from mathagent.agents import ManagerAgent


class RetrievalPipelineTest(unittest.TestCase):
    def test_select_retrieval_chunks_prefers_relevant_content(self) -> None:
        retriever = StaticRetriever(
            chunks=[
                RetrievalChunk(
                    source="paper_a",
                    title="Grey Forecasting",
                    content="Grey forecasting models are suitable for short time-series prediction.",
                    score=0.2,
                ),
                RetrievalChunk(
                    source="paper_b",
                    title="AHP Evaluation",
                    content="AHP is useful for multi-criteria evaluation and weighting.",
                    score=0.9,
                ),
            ]
        )

        result = retriever.retrieve("forecast demand with a short time series", problem_text="demo")
        selected = select_retrieval_chunks(result, query="forecast demand with a short time series", limit=1)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].source, "paper_a")

    def test_manager_persists_retrieval_context(self) -> None:
        retriever = StaticRetriever(
            name="static_demo",
            chunks=[
                RetrievalChunk(
                    source="contest_guide",
                    title="Modeling Guide",
                    content="Use explicit objectives, constraints, and evaluation metrics in each subproblem.",
                    score=0.8,
                )
            ],
        )
        memory = _EphemeralMemory()

        state = ManagerAgent().run(
            problem_text="建立优化与预测结合的数学建模方案。",
            tools=ToolRegistry.empty(),
            memory=memory,
            retriever=retriever,
        )

        self.assertEqual(state.stage, "done")
        self.assertEqual(state.retrieval.provider, "static_demo")
        self.assertTrue(state.retrieval.chunks)
        retrieval_json = json.loads(memory.get_shared("retrieval") or "{}")
        self.assertEqual(retrieval_json.get("provider"), "static_demo")
        self.assertTrue(retrieval_json.get("chunks"))

    def test_solver_context_includes_retrieval_payload(self) -> None:
        state = TaskState(problem_text="Forecast demand for the next week.")
        state.retrieval = StaticRetriever(
            chunks=[
                RetrievalChunk(
                    source="forecast_notes",
                    title="Forecast Notes",
                    content="Time-series models should preserve temporal ordering during validation.",
                )
            ]
        ).retrieve("Forecast demand for the next week.", problem_text=state.problem_text)
        subproblem = SubProblem(title="Problem 1", text="Forecast weekly demand.")
        state.subproblems.append(subproblem)

        context = _build_solver_context(state, subproblem, 1)
        retrieval_payload = context.get("retrieval") or {}

        self.assertEqual(retrieval_payload.get("provider"), "static")
        self.assertTrue(retrieval_payload.get("chunks"))
        rendered = format_retrieval_context(state.retrieval, query=subproblem.text)
        self.assertIn("forecast_notes", rendered)


if __name__ == "__main__":
    unittest.main()
