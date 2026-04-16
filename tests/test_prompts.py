import unittest

from mathagent.prompts import load_prompt, render_prompt


class PromptTemplateTest(unittest.TestCase):
    def test_load_prompt_from_templates(self) -> None:
        text = load_prompt("modeling_system")
        self.assertIn("mathematical modeling", text)

    def test_render_prompt_substitutes_variables(self) -> None:
        rendered = render_prompt(
            "writing_user",
            problem_text="demo",
            retrieval_context="retrieved reference",
            subproblems_json="[]",
            solver_runs_json="[]",
            review_findings_json="[]",
        )
        self.assertIn("demo", rendered)
        self.assertIn("[]", rendered)
        self.assertIn("retrieved reference", rendered)

    def test_coding_prompt_emphasizes_validation_not_algorithm_invention(self) -> None:
        text = load_prompt("coding_system")
        self.assertIn("validation agent", text)
        self.assertIn("Do not invent a brand-new algorithm", text)
        self.assertIn("multiple chart/image artifacts", text)


if __name__ == "__main__":
    unittest.main()
