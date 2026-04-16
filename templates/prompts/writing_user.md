Problem statement:
{problem_text}

Retrieved context (optional):
{retrieval_context}

Sub-problem analysis (JSON):
{subproblems_json}

Solver runs (JSON):
{solver_runs_json}

Review findings (JSON):
{review_findings_json}

Write Markdown with the following top-level sections:
- 摘要
- 问题重述
- 子问题分析与方法选择
- 模型假设与符号说明
- 求解与实验
- 结果与分析
- 审稿提示
- 结论与后续工作

Requirements:
- Use the exact subproblem titles from subproblems_json as subsection titles.
- For each subproblem, explain the model, algorithm, and solution steps.
- For each subproblem, cite at least one numeric_results field or one evidence marker from the corresponding solver run.
- If retrieved references are relevant, incorporate them as supporting background or modeling rationale instead of treating them as computed results.
- If figure_titles are present in a solver result, explicitly list those chart titles in the relevant section.
- If a solver run failed, is partial, has final_verdict=needs_review, or contains fallback/timeout recovery markers, state that clearly and downgrade the confidence of the conclusion.
- If the solver method differs from the modeling-stage chosen_method, mention the mismatch explicitly.
- Do not include placeholder constraints such as pending_constraint in polished modeling prose.
- If numeric_results only contain empty counters or trivial metadata, say that validation is incomplete instead of writing a full result claim.
- Do not dump raw stdout/stderr or repeated structured JSON into the paper body.
