Problem statement:
{problem_text}

Retrieved context (optional):
{retrieval_context}

Structured context JSON:
{context_json}

Return a JSON object with:
- summary: short string
- code: Python source code as a string

Requirements:
- The code should be self-contained and executable.
- It may read context.json from the current directory.
- It must write result.json using the required schema.
- It should write at least one additional artifact file summarizing the computation.
- The generated code should focus on the current subproblem only, not the whole task at once.
- Reuse the constraints, objective, and chosen method from the structured context instead of inventing a different task.
- Treat the algorithm as coming from the modeling context or the LLM reasoning chain, then verify it programmatically.
- Prefer producing rich backend charts plus structured validation outputs over designing a new fallback algorithm from scratch.
- Fill verification_checks, constraint_checks, error_metrics, robustness_checks, suspicious_points, and final_verdict whenever the computation supports them.
- If charts are generated, add a concise plot_code_hint that points to the plotting logic in the backend code.
- If retrieved references are useful, use them as methodological support, but keep the actual computation grounded in the current task data.
- If the problem is underspecified, report partial or failed honestly and explain what is missing.
- Do not use markdown fences inside the JSON string unless unavoidable.
