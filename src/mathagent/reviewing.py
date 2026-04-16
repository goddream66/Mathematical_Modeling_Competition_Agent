from __future__ import annotations

import re
from typing import Any

from .reporting import required_report_titles
from .state import SolverRun, TaskState

_PLACEHOLDER_CONSTRAINT_MARKERS = (
    "pending_constraint",
    "placeholder",
    "todo",
    "tbd",
    "constraints still need to be written",
)


def required_review_report_sections() -> list[str]:
    return required_report_titles()


def append_finding(
    findings: list[dict[str, str]],
    *,
    severity: str,
    area: str,
    message: str,
    suggestion: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "area": area,
            "message": message,
            "suggestion": suggestion,
        }
    )


def dedupe_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    output: list[dict[str, str]] = []
    for finding in findings:
        key = (
            str(finding.get("severity") or ""),
            str(finding.get("area") or ""),
            str(finding.get("message") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(finding)
    return output


def build_structural_review_findings(state: TaskState) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    _build_modeling_findings(findings, state)
    _build_solver_findings(findings, state)
    _build_report_findings(findings, state)
    return dedupe_findings(findings)


def has_blocking_review_findings(findings: list[dict[str, str]]) -> bool:
    blocking_messages = {
        "The results section does not explicitly cite solver evidence markers.",
    }
    return any(
        str(finding.get("severity") or "").lower() == "high"
        or str(finding.get("message") or "") in blocking_messages
        for finding in findings
    )


def _build_modeling_findings(findings: list[dict[str, str]], state: TaskState) -> None:
    for subproblem in state.subproblems:
        analysis = subproblem.analysis
        if not analysis.objective:
            append_finding(
                findings,
                severity="medium",
                area=subproblem.title,
                message=f"{subproblem.title} is missing an explicit objective.",
                suggestion="Add a clear objective or target output for this subproblem.",
            )
        if not analysis.chosen_method:
            append_finding(
                findings,
                severity="medium",
                area=subproblem.title,
                message=f"{subproblem.title} does not have a chosen primary method.",
                suggestion="Pick one main method from the candidate list and justify it.",
            )
        if not analysis.constraints:
            append_finding(
                findings,
                severity="medium",
                area=subproblem.title,
                message=f"{subproblem.title} still lacks explicit constraints.",
                suggestion="Translate hard and soft constraints from the problem statement into a list.",
            )
        elif any(_looks_like_placeholder_constraint(item) for item in analysis.constraints):
            append_finding(
                findings,
                severity="high",
                area=subproblem.title,
                message=f"{subproblem.title} still contains placeholder constraints.",
                suggestion="Replace pending or placeholder constraints with explicit hard/soft constraints before writing the final paper.",
            )
        if not analysis.formulation_steps:
            append_finding(
                findings,
                severity="medium",
                area=subproblem.title,
                message=f"{subproblem.title} does not yet contain explicit formulation steps.",
                suggestion="Write the model-building steps so the derivation can be audited and reproduced.",
            )
        if not analysis.assumptions:
            append_finding(
                findings,
                severity="low",
                area=subproblem.title,
                message=f"{subproblem.title} is missing explicit modeling assumptions.",
                suggestion="State the assumptions that connect the problem statement to the mathematical model.",
            )
        if not analysis.deliverables:
            append_finding(
                findings,
                severity="low",
                area=subproblem.title,
                message=f"{subproblem.title} does not define concrete deliverables.",
                suggestion="Specify what output this subproblem should produce, such as a prediction, ranking, or decision plan.",
            )
        confidence = analysis.confidence
        if confidence is not None and confidence < 0.45:
            append_finding(
                findings,
                severity="low",
                area=subproblem.title,
                message=f"{subproblem.title} has low modeling confidence ({confidence:.2f}).",
                suggestion="Revisit the decomposition or justify why the current method is still acceptable.",
            )


def _build_solver_findings(findings: list[dict[str, str]], state: TaskState) -> None:
    if not state.solver_runs:
        append_finding(
            findings,
            severity="high",
            area="coding",
            message="No executable solver runs were recorded.",
            suggestion="Run Coding again after improving the solver prompt or input data.",
        )
        return

    subproblem_by_title = {subproblem.title: subproblem for subproblem in state.subproblems}
    for run in state.solver_runs:
        subproblem = subproblem_by_title.get(run.subproblem_title)
        findings.extend(
            build_solver_repair_findings(
                run,
                getattr(subproblem, "analysis", None),
                context_text=str(getattr(subproblem, "text", "") or ""),
            )
        )
        _build_solver_metadata_findings(findings, run)


def build_solver_repair_findings(run: SolverRun, analysis: Any = None, *, context_text: str = "") -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    _append_core_solver_adequacy_findings(findings, run)
    _build_method_result_consistency_findings(findings, run, analysis, context_text=context_text)
    return dedupe_findings(findings)


def _append_core_solver_adequacy_findings(findings: list[dict[str, str]], run: SolverRun) -> None:
    structured = run.structured_result
    status = str(structured.get("status") or "")

    if not run.schema_valid:
        append_finding(
            findings,
            severity="high",
            area="coding",
            message=f"{run.subproblem_title} did not produce a valid structured result schema.",
            suggestion="Require the generated code to write a valid result.json before marking success.",
        )
    elif status == "partial":
        append_finding(
            findings,
            severity="medium",
            area="coding",
            message=f"{run.subproblem_title} only has a partial structured result.",
            suggestion="Replace the baseline/fallback logic with a domain-specific solver or add more data.",
        )
    elif status == "failed":
        append_finding(
            findings,
            severity="high",
            area="coding",
            message=f"{run.subproblem_title} returned a failed structured result.",
            suggestion="Inspect the generated code, stderr, and result.json for this subproblem.",
        )

    if _has_baseline_structured_solver_marker(structured):
        append_finding(
            findings,
            severity="high",
            area="coding",
            message=f"{run.subproblem_title} is still using baseline_structured_solver placeholder output.",
            suggestion="Replace the generic baseline solver with a domain-specific solver before treating this subproblem as solved.",
        )

    numeric_results = dict(structured.get("numeric_results", {}))
    if status == "ok" and not numeric_results:
        append_finding(
            findings,
            severity="medium",
            area=run.subproblem_title,
            message=f"{run.subproblem_title} reports success but does not expose any numeric results.",
            suggestion="Return at least one concrete metric, estimate, score, or decision value in numeric_results.",
        )

    next_steps = [str(item).strip() for item in structured.get("next_steps", []) if str(item).strip()]
    if status in {"partial", "failed"} and not next_steps:
        append_finding(
            findings,
            severity="low",
            area=run.subproblem_title,
            message=f"{run.subproblem_title} does not provide next steps after an incomplete run.",
            suggestion="List what data, constraints, or solver changes are needed to complete this subproblem.",
        )


def _build_solver_metadata_findings(findings: list[dict[str, str]], run: SolverRun) -> None:
    structured = run.structured_result
    artifact_names = [str(item).strip() for item in run.artifacts if str(item).strip()]
    figure_artifacts = [name for name in artifact_names if name.lower().endswith((".png", ".jpg", ".jpeg", ".svg"))]
    figure_titles = [str(item).strip() for item in structured.get("figure_titles", []) if str(item).strip()]
    if figure_artifacts and not figure_titles:
        append_finding(
            findings,
            severity="medium",
            area=run.subproblem_title,
            message=f"{run.subproblem_title} produced figure artifacts without figure_titles metadata.",
            suggestion="Add explicit figure_titles so the writing stage can cite charts correctly.",
        )


def _build_report_findings(findings: list[dict[str, str]], state: TaskState) -> None:
    if state.report_md is None:
        return

    if "## " not in state.report_md:
        append_finding(
            findings,
            severity="medium",
            area="writing",
            message="The report is missing detailed subsection headings.",
            suggestion="Add per-subproblem subsections and a dedicated results section.",
        )

    for run in state.solver_runs:
        if run.subproblem_title not in state.report_md:
            append_finding(
                findings,
                severity="low",
                area="writing",
                message=f"The report does not explicitly mention {run.subproblem_title}.",
                suggestion="Add a short paragraph summarizing the structured result for that subproblem.",
            )
        for title in [str(item).strip() for item in run.structured_result.get("figure_titles", []) if str(item).strip()]:
            if title not in state.report_md:
                append_finding(
                    findings,
                    severity="medium",
                    area="writing",
                    message=f"The report does not explicitly cite figure title '{title}'.",
                    suggestion="Mention each generated chart title in the relevant experiment or results section.",
                )


def _build_method_result_consistency_findings(
    findings: list[dict[str, str]],
    run: SolverRun,
    analysis: Any,
    *,
    context_text: str = "",
) -> None:
    structured = run.structured_result
    numeric_results = {str(key).lower(): value for key, value in dict(structured.get("numeric_results", {})).items()}
    evidence_markers = [str(item).lower() for item in structured.get("evidence", []) if str(item).strip()]
    text_parts = [
        run.subproblem_title,
        context_text,
        str(structured.get("method") or ""),
        str(structured.get("objective") or ""),
        " ".join(evidence_markers),
    ]
    if analysis is not None:
        chosen_method = str(getattr(analysis, "chosen_method", "") or "")
        executed_method = str(structured.get("method") or "")
        if chosen_method and executed_method and _methods_materially_differ(chosen_method, executed_method):
            append_finding(
                findings,
                severity="high",
                area=run.subproblem_title,
                message=f"{run.subproblem_title} executed method '{executed_method}' does not match modeling method '{chosen_method}'.",
                suggestion="Either rerun coding with the modeled method or explain the method switch explicitly in the report.",
            )
        text_parts.extend(
            [
                str(getattr(analysis, "objective", "") or ""),
                str(getattr(analysis, "chosen_method", "") or ""),
                " ".join(str(item) for item in getattr(analysis, "task_types", []) if str(item).strip()),
                " ".join(str(item) for item in getattr(analysis, "candidate_models", []) if str(item).strip()),
            ]
        )
    normalized = " ".join(text_parts).lower()

    if _looks_like_forecast_problem(normalized):
        if not _has_any_numeric_key(numeric_results, "forecast", "predict", "trend", "error", "rmse", "mape", "mae"):
            append_finding(
                findings,
                severity="medium",
                area=run.subproblem_title,
                message=f"{run.subproblem_title} looks like a forecasting task, but the result is missing forecast values or error metrics.",
                suggestion="Expose forecast outputs, trend indicators, or at least one error metric such as MAE, RMSE, or MAPE.",
            )

    if _looks_like_optimization_problem(normalized):
        if not _has_any_numeric_key(numeric_results, "objective", "cost", "profit", "value", "budget", "selected", "score"):
            append_finding(
                findings,
                severity="medium",
                area=run.subproblem_title,
                message=f"{run.subproblem_title} looks like an optimization task, but the result is missing objective or allocation metrics.",
                suggestion="Return objective value, total cost/profit, budget usage, selected count, or other decision-quality metrics.",
            )

    if _looks_like_path_problem(normalized):
        if not _has_any_numeric_key(numeric_results, "path", "distance", "cost", "length", "node", "edge"):
            append_finding(
                findings,
                severity="medium",
                area=run.subproblem_title,
                message=f"{run.subproblem_title} looks like a path/network task, but the result is missing path or distance metrics.",
                suggestion="Return path cost, distance, traversed nodes, edge count, or related network metrics.",
            )

    if _looks_like_evaluation_problem(normalized):
        if not _has_any_numeric_key(numeric_results, "score", "rank", "weight", "indicator", "entropy", "topsis"):
            append_finding(
                findings,
                severity="medium",
                area=run.subproblem_title,
                message=f"{run.subproblem_title} looks like an evaluation/ranking task, but the result is missing scores, ranks, or weights.",
                suggestion="Return indicator scores, ranking outputs, weights, or aggregated evaluation metrics.",
            )


def _has_baseline_structured_solver_marker(structured_result: dict[str, Any]) -> bool:
    evidence = [str(item).strip() for item in structured_result.get("evidence", []) if str(item).strip()]
    return "template_used=baseline_structured_solver" in evidence


def _has_any_numeric_key(numeric_results: dict[str, Any], *keywords: str) -> bool:
    keys = list(numeric_results.keys())
    return any(any(keyword in key for keyword in keywords) for key in keys)


def _looks_like_forecast_problem(text: str) -> bool:
    return _matches_keywords(text, "forecast", "predict", "time series", "regression", "fit", "预测", "拟合")


def _looks_like_optimization_problem(text: str) -> bool:
    return _matches_keywords(text, "optimiz", "decision", "allocation", "budget", "profit", "cost", "优化", "决策", "规划")


def _looks_like_path_problem(text: str) -> bool:
    return _matches_keywords(text, "path", "route", "network", "shortest", "distance", "routing", "路径", "网络")


def _looks_like_evaluation_problem(text: str) -> bool:
    return _matches_keywords(text, "evaluation", "weight", "rank", "score", "topsis", "ahp", "评价", "排序", "权重")


def _matches_keywords(text: str, *keywords: str) -> bool:
    normalized = re.sub(r"\s+", " ", text or "").lower()
    return any(keyword in normalized for keyword in keywords)


def _looks_like_placeholder_constraint(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return any(marker in normalized for marker in _PLACEHOLDER_CONSTRAINT_MARKERS)


def _methods_materially_differ(chosen_method: str, executed_method: str) -> bool:
    chosen = _normalize_method(chosen_method)
    executed = _normalize_method(executed_method)
    if not chosen or not executed or chosen == executed:
        return False
    return chosen not in executed and executed not in chosen


def _normalize_method(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("/", " ").replace("-", " ").replace("_", " ")
    return " ".join(text.split())
