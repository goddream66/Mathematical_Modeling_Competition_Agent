from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..llm import Message, build_llm
from ..llm.config import load_llm_config
from ..llm.utils import extract_first_json
from ..memory import MemoryStore
from ..prompts import render_prompt
from ..reviewing import (
    build_solver_repair_findings,
    build_structural_review_findings,
    dedupe_findings,
    has_blocking_review_findings,
    required_review_report_sections,
)
from ..retrieval import format_retrieval_context, retrieval_result_to_payload
from ..reporting import inject_figure_titles, stabilize_report_markdown
from ..solvers import build_fallback_solver_code as builtin_build_fallback_solver_code
from ..skills import (
    ClarifySkill,
    ModelSkill,
    ProblemDecomposeSkill,
    ReportSkill,
    SolveSkill,
    SubProblemAnalyzeSkill,
    ValidateSkill,
)
from ..state import ExperimentArtifact, SolverRun, SubProblem, TaskState
from ..tools import ToolRegistry
from ..verification.checkers import (
    build_report_sources,
    build_verification_findings,
    build_verification_summary,
)


RESULT_STATUS_VALUES = {"ok", "partial", "failed"}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        clean = str(item).strip()
        if clean:
            items.append(clean)
    return items


def _figure_titles(value: Any) -> list[str]:
    return _string_list(value)


def _check_list(value: Any) -> list[str]:
    return _string_list(value)


def _final_verdict(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    return verdict if verdict in {"validated", "needs_review", "failed"} else ""


_PLACEHOLDER_TEXT_MARKERS = (
    "formal constraints still need to be written explicitly",
    "constraints still need to be written",
    "placeholder",
    "todo",
    "tbd",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _is_placeholder_text(value: Any) -> bool:
    text = _clean_text(value).lower()
    if not text:
        return True
    return any(marker in text for marker in _PLACEHOLDER_TEXT_MARKERS)


def _clean_constraints(value: Any) -> list[str]:
    constraints = _string_list(value)
    return [item for item in constraints if not _is_placeholder_text(item)]


def _prefer_existing_title(candidate_title: str, fallback_title: str) -> str:
    title = candidate_title.strip()
    if not title:
        return fallback_title
    normalized = title.lower()
    if re.fullmatch(r"(subproblem|problem)\s*\d+", normalized):
        return fallback_title
    return title


def _subproblem_payload(subproblem: SubProblem) -> dict[str, Any]:
    return {
        "title": subproblem.title,
        "text": subproblem.text,
        "analysis": {
            "task_types": subproblem.analysis.task_types,
            "candidate_models": subproblem.analysis.candidate_models,
            "solution_plan": subproblem.analysis.solution_plan,
            "key_variables": subproblem.analysis.key_variables,
            "needed_data": subproblem.analysis.needed_data,
            "evaluation": subproblem.analysis.evaluation,
            "notes": subproblem.analysis.notes,
            "objective": subproblem.analysis.objective,
            "constraints": subproblem.analysis.constraints,
            "assumptions": subproblem.analysis.assumptions,
            "deliverables": subproblem.analysis.deliverables,
            "formulation_steps": subproblem.analysis.formulation_steps,
            "chosen_method": subproblem.analysis.chosen_method,
            "confidence": subproblem.analysis.confidence,
        },
    }


def _subproblems_payload(state: TaskState) -> list[dict[str, Any]]:
    return [_subproblem_payload(subproblem) for subproblem in state.subproblems]


def _solver_runs_payload(state: TaskState) -> list[dict[str, Any]]:
    return [
        {
            "subproblem_title": run.subproblem_title,
            "success": run.success,
            "summary": run.summary,
            "stdout": run.stdout,
            "stderr": run.stderr,
            "artifacts": run.artifacts,
            "schema_valid": run.schema_valid,
            "structured_result": run.structured_result,
        }
        for run in state.solver_runs
    ]


def _retrieval_payload(state: TaskState, *, query: str, limit: int = 4) -> dict[str, Any]:
    return retrieval_result_to_payload(state.retrieval, query=query, limit=limit)


def _retrieval_prompt_context(state: TaskState, *, query: str, limit: int = 4) -> str:
    return format_retrieval_context(state.retrieval, query=query, limit=limit)


def _load_solver_artifacts(run_dir: str, artifact_names: list[str]) -> list[ExperimentArtifact]:
    base_path = Path(run_dir)
    artifacts: list[ExperimentArtifact] = []
    for artifact_name in artifact_names:
        artifact_path = base_path / artifact_name
        if not artifact_path.exists() or not artifact_path.is_file():
            continue
        suffix = artifact_path.suffix.lower()
        if suffix == ".json":
            try:
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
                kind = "json"
            except Exception:
                payload = artifact_path.read_text(encoding="utf-8", errors="replace")
                kind = "text"
        elif suffix in {".png", ".jpg", ".jpeg", ".svg"}:
            payload = {"path": str(artifact_path), "name": artifact_name}
            kind = "figure"
        elif suffix == ".py":
            payload = artifact_path.read_text(encoding="utf-8", errors="replace")
            kind = "code"
        else:
            payload = artifact_path.read_text(encoding="utf-8", errors="replace")
            kind = "text"
        artifacts.append(ExperimentArtifact(name=artifact_name, kind=kind, payload=payload))
    return artifacts


def _build_solver_context(state: TaskState, subproblem: SubProblem, index: int) -> dict[str, Any]:
    retrieval_query = subproblem.text or subproblem.title or state.problem_text
    return {
        "problem_text": state.problem_text,
        "clarifications": state.clarifications,
        "subproblem_index": index,
        "subproblem": _subproblem_payload(subproblem),
        "all_subproblems": _subproblems_payload(state),
        "input_data": state.input_data,
        "retrieval": _retrieval_payload(state, query=retrieval_query, limit=4),
        "model": {
            "assumptions": state.model.assumptions,
            "constraints": state.model.constraints,
            "method_candidates": state.model.method_candidates,
            "chosen_method": state.model.chosen_method,
            "formulation_outline": state.model.formulation_outline,
            "evidence_gaps": state.model.evidence_gaps,
        },
    }


def _extract_code_block(text: str) -> str:
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def _normalize_numeric_results(value: Any) -> dict[str, float | int | str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, float | int | str] = {}
    for key, raw in value.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            normalized[clean_key] = raw
        else:
            normalized[clean_key] = str(raw).strip()
    return normalized


def _error_metrics_from_numeric_results(numeric_results: dict[str, float | int | str]) -> dict[str, float | int | str]:
    metrics: dict[str, float | int | str] = {}
    keywords = ("error", "mae", "rmse", "mape", "residual", "loss", "accuracy", "precision", "recall", "f1", "score")
    for key, value in numeric_results.items():
        lowered = str(key).lower()
        if any(keyword in lowered for keyword in keywords):
            metrics[str(key)] = value
    return metrics


def _synthesize_evidence(normalized: dict[str, Any]) -> list[str]:
    evidence = _string_list(normalized.get("evidence"))
    if evidence:
        return evidence

    synthesized = ["auto_evidence=synthesized_from_available_outputs"]
    numeric_results = normalized.get("numeric_results") or {}
    if isinstance(numeric_results, dict) and numeric_results:
        numeric_keys = list(numeric_results.keys())[:4]
        synthesized.append(f"numeric_result_keys={','.join(numeric_keys)}")
    figure_titles = _figure_titles(normalized.get("figure_titles"))
    if figure_titles:
        synthesized.append(f"figure_title={figure_titles[0]}")
    artifacts = _string_list(normalized.get("artifacts"))
    if artifacts:
        synthesized.append(f"artifact_names={','.join(artifacts[:3])}")
    status = str(normalized.get("status") or "").strip().lower()
    if status:
        synthesized.append(f"result_status={status}")
    method = str(normalized.get("method") or "").strip()
    if method:
        synthesized.append(f"method_marker={method}")
    summary = str(normalized.get("result_summary") or "").strip()
    if summary and len(synthesized) == 1:
        synthesized.append(f"summary_marker={summary[:120]}")
    return [item for item in synthesized if item]


def _validate_result_schema(payload: Any, expected_title: str) -> tuple[bool, dict[str, Any], str]:
    if not isinstance(payload, dict):
        return False, {}, "structured result is not a JSON object"

    normalized = {
        "subproblem_title": str(payload.get("subproblem_title") or "").strip(),
        "status": str(payload.get("status") or "").strip().lower(),
        "method": str(payload.get("method") or "").strip(),
        "objective": str(payload.get("objective") or "").strip(),
        "assumptions": _string_list(payload.get("assumptions")),
        "constraints": _clean_constraints(payload.get("constraints")),
        "result_summary": str(payload.get("result_summary") or "").strip(),
        "evidence": _string_list(payload.get("evidence")),
        "numeric_results": _normalize_numeric_results(payload.get("numeric_results")),
        "figure_titles": _figure_titles(payload.get("figure_titles")),
        "artifacts": _string_list(payload.get("artifacts")),
        "next_steps": _string_list(payload.get("next_steps")),
        "verification_checks": _check_list(payload.get("verification_checks")),
        "constraint_checks": _check_list(payload.get("constraint_checks")),
        "error_metrics": _normalize_numeric_results(payload.get("error_metrics")),
        "robustness_checks": _check_list(payload.get("robustness_checks")),
        "suspicious_points": _check_list(payload.get("suspicious_points")),
        "final_verdict": _final_verdict(payload.get("final_verdict")),
        "plot_code_hint": str(payload.get("plot_code_hint") or "").strip(),
    }
    normalized["evidence"] = _synthesize_evidence(normalized)
    if not normalized["error_metrics"]:
        normalized["error_metrics"] = _error_metrics_from_numeric_results(normalized["numeric_results"])

    if not normalized["subproblem_title"]:
        return False, normalized, "missing subproblem_title"
    if normalized["subproblem_title"] != expected_title:
        return False, normalized, "subproblem_title does not match current subproblem"
    if normalized["status"] not in RESULT_STATUS_VALUES:
        return False, normalized, "status must be one of ok/partial/failed"
    if not normalized["method"]:
        return False, normalized, "missing method"
    if not normalized["result_summary"]:
        return False, normalized, "missing result_summary"
    if not normalized["evidence"]:
        return False, normalized, "evidence must contain at least one item"
    return True, normalized, ""


def _extract_json_candidate(stdout_text: str) -> Any:
    last_line = stdout_text.splitlines()[-1]
    try:
        return json.loads(last_line)
    except Exception:
        return extract_first_json(stdout_text)


def _extract_structured_result(run_dir: str, artifacts: list[str], stdout: str, expected_title: str) -> tuple[bool, dict[str, Any], str]:
    base_path = Path(run_dir)
    if "result.json" in artifacts:
        candidate = base_path / "result.json"
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, {}, f"failed to parse result.json: {exc}"
        return _validate_result_schema(payload, expected_title)

    stdout_text = stdout.strip()
    if stdout_text:
        try:
            payload = _extract_json_candidate(stdout_text)
        except Exception:
            return False, {}, "missing result.json and stdout is not valid JSON"
        return _validate_result_schema(payload, expected_title)
    return False, {}, "missing result.json and empty stdout"


def _code_is_syntax_valid(code: str) -> tuple[bool, str]:
    source = code.strip()
    if not source:
        return False, "generated code is empty"
    try:
        ast.parse(source)
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "unknown line"
        detail = exc.msg or "invalid syntax"
        return False, f"{detail} at {location}"
    return True, ""


def _should_retry_with_fallback(*, code: str, fallback_code: str, run_success: bool, schema_valid: bool, stderr: str, schema_error: str) -> bool:
    if code == fallback_code:
        return False
    if run_success and schema_valid:
        return False
    combined = "\n".join(part for part in [stderr, schema_error] if part).lower()
    retry_markers = (
        "syntaxerror",
        "invalid syntax",
        "unterminated string literal",
        "indentationerror",
        "typeerror: list.append() takes no keyword arguments",
        "missing result.json",
        "failed to parse result.json",
    )
    return any(marker in combined for marker in retry_markers)


def _derive_verification_checks(
    *,
    run_success: bool,
    schema_valid: bool,
    structured_result: dict[str, Any],
    artifacts: list[str],
) -> list[str]:
    checks = [str(item).strip() for item in structured_result.get("verification_checks", []) if str(item).strip()]
    observed = set(checks)

    derived = [
        f"python_execution:{'passed' if run_success else 'failed'}",
        f"structured_schema:{'passed' if schema_valid else 'failed'}",
        f"numeric_results:{'present' if dict(structured_result.get('numeric_results', {})) else 'missing'}",
        f"figure_artifacts:{'present' if any(name.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')) for name in artifacts) else 'missing'}",
    ]
    if str(structured_result.get("status") or "") in {"partial", "failed"}:
        derived.append(f"solver_status:{structured_result.get('status')}")
    for item in derived:
        if item not in observed:
            checks.append(item)
            observed.add(item)
    return checks


def _derive_constraint_checks(structured_result: dict[str, Any]) -> list[str]:
    existing = [str(item).strip() for item in structured_result.get("constraint_checks", []) if str(item).strip()]
    observed = set(existing)
    status = str(structured_result.get("status") or "unknown")
    constraints = [str(item).strip() for item in structured_result.get("constraints", []) if str(item).strip()]
    if not constraints:
        item = "constraint_review:constraints_not_explicitly_checkable"
        return existing + ([item] if item not in observed else [])

    derived: list[str] = []
    limit = min(len(constraints), 3)
    for index in range(limit):
        derived.append(f"constraint_{index + 1}:{status}")
    for item in derived:
        if item not in observed:
            existing.append(item)
            observed.add(item)
    return existing


def _derive_robustness_checks(structured_result: dict[str, Any]) -> list[str]:
    existing = [str(item).strip() for item in structured_result.get("robustness_checks", []) if str(item).strip()]
    observed = set(existing)
    numeric_results = dict(structured_result.get("numeric_results", {}))
    error_metrics = dict(structured_result.get("error_metrics", {}))
    evidence = [str(item).strip() for item in structured_result.get("evidence", []) if str(item).strip()]
    derived: list[str] = []

    if error_metrics:
        derived.append("metric_review:error_metrics_present")
    if any("backtest" in str(key).lower() or "validation" in str(key).lower() for key in numeric_results):
        derived.append("temporal_validation:present")
    if any("sensitivity" in item.lower() or "robust" in item.lower() for item in evidence):
        derived.append("sensitivity_check:present")
    if not derived:
        derived.append("robustness_review:manual_follow_up_recommended")

    for item in derived:
        if item not in observed:
            existing.append(item)
            observed.add(item)
    return existing


def _derive_suspicious_points(
    *,
    stderr: str,
    structured_result: dict[str, Any],
    repair_findings: list[dict[str, str]] | None = None,
) -> list[str]:
    existing = [str(item).strip() for item in structured_result.get("suspicious_points", []) if str(item).strip()]
    observed = set(existing)
    if stderr.strip():
        item = "runtime_warning:stderr_present"
        if item not in observed:
            existing.append(item)
            observed.add(item)
    if str(structured_result.get("status") or "") == "partial":
        item = "result_status:partial"
        if item not in observed:
            existing.append(item)
            observed.add(item)
    for finding in repair_findings or []:
        message = str(finding.get("message") or "").strip()
        if message and message not in observed:
            existing.append(message)
            observed.add(message)
    return existing


def _derive_final_verdict(*, run_success: bool, schema_valid: bool, structured_result: dict[str, Any]) -> str:
    existing = _final_verdict(structured_result.get("final_verdict"))
    if existing:
        return existing
    status = str(structured_result.get("status") or "")
    if not run_success or not schema_valid or status == "failed":
        return "failed"
    if status == "partial":
        return "needs_review"
    if dict(structured_result.get("numeric_results", {})):
        return "validated"
    return "needs_review"


def _enrich_structured_result(
    *,
    structured_result: dict[str, Any],
    run_success: bool,
    schema_valid: bool,
    stderr: str,
    artifacts: list[str],
    script_name: str,
    repair_findings: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    updated = dict(structured_result)
    updated["error_metrics"] = _normalize_numeric_results(updated.get("error_metrics")) or _error_metrics_from_numeric_results(
        dict(updated.get("numeric_results", {}))
    )
    updated["verification_checks"] = _derive_verification_checks(
        run_success=run_success,
        schema_valid=schema_valid,
        structured_result=updated,
        artifacts=artifacts,
    )
    updated["constraint_checks"] = _derive_constraint_checks(updated)
    updated["robustness_checks"] = _derive_robustness_checks(updated)
    updated["suspicious_points"] = _derive_suspicious_points(
        stderr=stderr,
        structured_result=updated,
        repair_findings=repair_findings,
    )
    updated["final_verdict"] = _derive_final_verdict(
        run_success=run_success,
        schema_valid=schema_valid,
        structured_result=updated,
    )
    if not str(updated.get("plot_code_hint") or "").strip() and updated.get("figure_titles"):
        updated["plot_code_hint"] = f"See {script_name} for backend chart generation code."
    return updated


def _build_solver_repair_signals(
    subproblem: SubProblem,
    *,
    run_success: bool,
    summary: str,
    code: str,
    stdout: str,
    stderr: str,
    artifacts: list[str],
    structured_result: dict[str, Any],
    schema_valid: bool,
) -> list[dict[str, str]]:
    candidate = SolverRun(
        subproblem_title=subproblem.title,
        success=run_success and schema_valid and structured_result.get("status") in {"ok", "partial"},
        summary=summary,
        code=code,
        stdout=stdout,
        stderr=stderr,
        artifacts=artifacts,
        structured_result=structured_result,
        schema_valid=schema_valid,
    )
    return build_solver_repair_findings(candidate, subproblem.analysis, context_text=subproblem.text)


def _repair_findings_weight(findings: list[dict[str, str]]) -> int:
    weights = {"high": 3, "medium": 2, "low": 1}
    return sum(weights.get(str(item.get("severity") or "").lower(), 1) for item in findings)


def _summarize_repair_findings(findings: list[dict[str, str]]) -> str:
    messages = [str(item.get("message") or "").strip() for item in findings if str(item.get("message") or "").strip()]
    return "; ".join(messages[:2])


def _prefer_fallback_repair_candidate(
    current_result: dict[str, Any],
    current_findings: list[dict[str, str]],
    fallback_schema_valid: bool,
    fallback_result: dict[str, Any],
    fallback_findings: list[dict[str, str]],
) -> bool:
    if not fallback_schema_valid or not fallback_result:
        return False

    current_score = _repair_findings_weight(current_findings)
    fallback_score = _repair_findings_weight(fallback_findings)
    if fallback_score < current_score:
        return True

    current_status = str(current_result.get("status") or "")
    fallback_status = str(fallback_result.get("status") or "")
    return current_status in {"partial", "failed"} and fallback_status == "ok"


def _downgrade_weak_result(structured_result: dict[str, Any], findings: list[dict[str, str]]) -> dict[str, Any]:
    if not structured_result or not findings:
        return structured_result

    updated = dict(structured_result)
    if str(updated.get("status") or "") == "ok":
        updated["status"] = "partial"

    summary = str(updated.get("result_summary") or "").strip()
    issue_summary = _summarize_repair_findings(findings)
    repair_note = "Auto-check flagged incomplete solver evidence."
    if issue_summary:
        repair_note = f"Auto-check flagged incomplete solver evidence: {issue_summary}"
    if repair_note not in summary:
        updated["result_summary"] = f"{summary} {repair_note}".strip()

    evidence = [str(item).strip() for item in updated.get("evidence", []) if str(item).strip()]
    if "auto_check=repair_needed" not in evidence:
        evidence.append("auto_check=repair_needed")
    updated["evidence"] = evidence

    next_steps = [str(item).strip() for item in updated.get("next_steps", []) if str(item).strip()]
    for finding in findings:
        suggestion = str(finding.get("suggestion") or "").strip()
        if suggestion and suggestion not in next_steps:
            next_steps.append(suggestion)
    updated["next_steps"] = next_steps
    return updated



def _build_fallback_solver_code(context: dict[str, Any]) -> tuple[str, str]:
    return builtin_build_fallback_solver_code(context)


def _build_llm_solver(state: TaskState, subproblem: SubProblem, index: int) -> tuple[str, str]:
    context = _build_solver_context(state, subproblem, index)
    fallback_summary, fallback_code = _build_fallback_solver_code(context)
    cfg = load_llm_config("CODING")
    if cfg is None:
        return fallback_summary, fallback_code

    llm = build_llm(cfg)
    response = llm.chat(
        [
            Message(role="system", content=render_prompt("coding_system")),
            Message(
                role="user",
                content=render_prompt(
                    "coding_user",
                    problem_text=state.problem_text,
                    retrieval_context=_retrieval_prompt_context(
                        state,
                        query=subproblem.text or subproblem.title or state.problem_text,
                        limit=4,
                    ),
                    context_json=json.dumps(context, ensure_ascii=False, indent=2),
                ),
            ),
        ],
        temperature=0.1,
    )
    try:
        payload = extract_first_json(response)
        if isinstance(payload, dict):
            summary = str(payload.get("summary") or "").strip() or f"Generated solver for {subproblem.title}."
            code = _extract_code_block(str(payload.get("code") or ""))
            if code:
                is_valid, syntax_error = _code_is_syntax_valid(code)
                if is_valid:
                    return summary, code
                return (
                    f"{fallback_summary} Fallback was used because generated code had invalid syntax: {syntax_error}.",
                    fallback_code,
                )
    except Exception:
        pass

    code = _extract_code_block(response)
    if code:
        is_valid, syntax_error = _code_is_syntax_valid(code)
        if is_valid:
            return f"Generated solver for {subproblem.title}.", code
        return (
            f"{fallback_summary} Fallback was used because generated code had invalid syntax: {syntax_error}.",
            fallback_code,
        )
    return fallback_summary, fallback_code


def _required_report_sections() -> list[str]:
    return required_review_report_sections()


def _summarize_solver_runs(runs: list[SolverRun]) -> str:
    if not runs:
        return "No solver runs were produced."
    lines: list[str] = []
    for run in runs:
        status = run.structured_result.get("status") or "invalid"
        summary = run.structured_result.get("result_summary") or run.summary
        lines.append(f"{run.subproblem_title}: {status} - {summary}")
    return "\n".join(lines)


def _overall_solver_status(runs: list[SolverRun]) -> str:
    if not runs:
        return "solver_failed"
    if any(not run.success or not run.schema_valid for run in runs):
        return "solver_failed"
    statuses = {str(run.structured_result.get("status") or "") for run in runs}
    if statuses == {"ok"}:
        return "solved"
    if "failed" in statuses:
        return "solver_failed"
    return "partially_solved"


@dataclass(frozen=True)
class ModelingAgent:
    name: str = "modeling"

    def run(self, state: TaskState, tools: ToolRegistry, memory: MemoryStore) -> TaskState:
        state = ProblemDecomposeSkill().run(state, tools)
        state = SubProblemAnalyzeSkill().run(state, tools)
        state = ClarifySkill().run(state, tools)
        state = ModelSkill().run(state, tools)

        cfg = load_llm_config("MODELING")
        if cfg is not None:
            llm = build_llm(cfg)
            try:
                existing_titles = [subproblem.title for subproblem in state.subproblems]
                payload = extract_first_json(
                    llm.chat(
                        [
                            Message(role="system", content=render_prompt("modeling_system")),
                            Message(
                                role="user",
                                content=render_prompt(
                                    "modeling_user",
                                    problem_text=state.problem_text,
                                    retrieval_context=_retrieval_prompt_context(
                                        state,
                                        query=state.problem_text,
                                        limit=6,
                                    ),
                                    existing_subproblems_json=json.dumps(
                                        _subproblems_payload(state),
                                        ensure_ascii=False,
                                        indent=2,
                                    ),
                                ),
                            ),
                        ],
                        temperature=0.2,
                    )
                )
                if isinstance(payload, list) and payload:
                    state.subproblems = []
                    for index, item in enumerate(payload, start=1):
                        if not isinstance(item, dict):
                            continue
                        fallback_title = existing_titles[index - 1] if index - 1 < len(existing_titles) else f"Subproblem {index}"
                        subproblem = SubProblem(
                            title=_prefer_existing_title(str(item.get("title") or "").strip(), fallback_title),
                            text=str(item.get("text") or "").strip(),
                        )
                        analysis = subproblem.analysis
                        analysis.task_types = _string_list(item.get("task_types"))
                        analysis.candidate_models = _string_list(item.get("candidate_models"))
                        analysis.solution_plan = _string_list(item.get("solution_plan"))
                        analysis.key_variables = _string_list(item.get("key_variables"))
                        analysis.needed_data = _string_list(item.get("needed_data"))
                        analysis.evaluation = _string_list(item.get("evaluation"))
                        analysis.notes = _string_list(item.get("notes"))
                        analysis.objective = str(item.get("objective") or "").strip() or None
                        analysis.constraints = _clean_constraints(item.get("constraints"))
                        analysis.assumptions = _string_list(item.get("assumptions"))
                        analysis.deliverables = _string_list(item.get("deliverables"))
                        analysis.formulation_steps = _string_list(item.get("formulation_steps"))
                        analysis.chosen_method = str(item.get("chosen_method") or "").strip() or None
                        if isinstance(item.get("confidence"), (float, int)):
                            analysis.confidence = float(item["confidence"])
                        state.subproblems.append(subproblem)
                    state = ClarifySkill().run(state, tools)
                    state = ModelSkill().run(state, tools)
            except Exception as exc:
                memory.set_agent_json(self.name, "llm_error", {"error": str(exc)})
                memory.append_event("agent", self.name, "llm_error", {"error": str(exc)})

        memory.set_shared("problem_text", state.problem_text)
        memory.set_shared_json("retrieval", _retrieval_payload(state, query=state.problem_text, limit=6))
        memory.set_shared_json("subproblems", _subproblems_payload(state))
        memory.set_agent_json(self.name, "clarifications", state.clarifications)
        memory.set_agent_json(
            self.name,
            "model_overview",
            {
                "chosen_method": state.model.chosen_method,
                "method_candidates": state.model.method_candidates,
                "assumptions": state.model.assumptions,
                "constraints": state.model.constraints,
                "formulation_outline": state.model.formulation_outline,
            },
        )
        memory.append_event("agent", self.name, "done", {"stage": state.stage})
        return state


@dataclass(frozen=True)
class CodingAgent:
    name: str = "coding"

    def run(self, state: TaskState, tools: ToolRegistry, memory: MemoryStore) -> TaskState:
        tool = tools.maybe_get("python_exec")
        if tool is None:
            state.results["status"] = "solver_unavailable"
            state.results["solver_summary"] = "No python execution tool is registered."
            state = SolveSkill().run(state, tools)
            memory.set_agent_json(
                self.name,
                "solver_result",
                {"status": state.results.get("status"), "summary": state.results.get("solver_summary")},
            )
            memory.append_event("agent", self.name, "done", {"stage": state.stage})
            return state

        state.solver_runs = []
        structured_results: list[dict[str, Any]] = []
        for index, subproblem in enumerate(state.subproblems, start=1):
            context = _build_solver_context(state, subproblem, index)
            fallback_summary, fallback_code = _build_fallback_solver_code(context)
            current_filename = f"solver_{index}.py"
            generation_error = ""
            try:
                summary, code = _build_llm_solver(state, subproblem, index)
            except Exception as exc:
                summary, code = fallback_summary, fallback_code
                generation_error = str(exc)

            result = tool.run(
                {
                    "code": code,
                    "filename": current_filename,
                    "context": context,
                    "timeout_s": 20.0,
                }
            )
            run_success = bool(result.get("success"))
            schema_valid, structured_result, schema_error = _extract_structured_result(
                str(result.get("run_dir") or ""),
                [str(name) for name in result.get("artifacts") or []],
                str(result.get("stdout") or ""),
                subproblem.title,
            )
            stderr_text = str(result.get("stderr") or "")
            if generation_error:
                stderr_text = (stderr_text + f"\nRecovered from CODING generation failure: {generation_error}").strip()

            if _should_retry_with_fallback(
                code=code,
                fallback_code=fallback_code,
                run_success=run_success,
                schema_valid=schema_valid,
                stderr=stderr_text,
                schema_error=schema_error,
            ):
                fallback_result = tool.run(
                    {
                        "code": fallback_code,
                        "filename": f"solver_{index}_fallback.py",
                        "context": context,
                        "timeout_s": 20.0,
                    }
                )
                fallback_run_success = bool(fallback_result.get("success"))
                fallback_schema_valid, fallback_structured_result, fallback_schema_error = _extract_structured_result(
                    str(fallback_result.get("run_dir") or ""),
                    [str(name) for name in fallback_result.get("artifacts") or []],
                    str(fallback_result.get("stdout") or ""),
                    subproblem.title,
                )
                if fallback_run_success or fallback_schema_valid:
                    stderr_parts = [stderr_text, "Retried with fallback solver after CODING execution failure."]
                    fallback_stderr = str(fallback_result.get("stderr") or "")
                    if fallback_stderr:
                        stderr_parts.append(f"Fallback stderr: {fallback_stderr}")
                    if fallback_schema_error:
                        stderr_parts.append(f"Fallback schema validation failed: {fallback_schema_error}")
                    stderr_text = "\n".join(part for part in stderr_parts if part).strip()
                    result = fallback_result
                    run_success = fallback_run_success
                    schema_valid = fallback_schema_valid
                    structured_result = fallback_structured_result
                    schema_error = fallback_schema_error
                    summary = f"{fallback_summary} Retried automatically after CODING execution failed."
                    code = fallback_code
                    current_filename = f"solver_{index}_fallback.py"

            repair_findings: list[dict[str, str]] = []
            if schema_valid and structured_result:
                repair_findings = _build_solver_repair_signals(
                    subproblem,
                    run_success=run_success,
                    summary=summary,
                    code=code,
                    stdout=str(result.get("stdout") or ""),
                    stderr=stderr_text,
                    artifacts=[str(name) for name in result.get("artifacts") or []],
                    structured_result=structured_result,
                    schema_valid=schema_valid,
                )

            if repair_findings and code != fallback_code:
                repair_reason = _summarize_repair_findings(repair_findings)
                fallback_result = tool.run(
                    {
                        "code": fallback_code,
                        "filename": f"solver_{index}_fallback.py",
                        "context": context,
                        "timeout_s": 20.0,
                    }
                )
                fallback_run_success = bool(fallback_result.get("success"))
                fallback_schema_valid, fallback_structured_result, fallback_schema_error = _extract_structured_result(
                    str(fallback_result.get("run_dir") or ""),
                    [str(name) for name in fallback_result.get("artifacts") or []],
                    str(fallback_result.get("stdout") or ""),
                    subproblem.title,
                )
                fallback_findings: list[dict[str, str]] = []
                if fallback_schema_valid and fallback_structured_result:
                    fallback_findings = _build_solver_repair_signals(
                        subproblem,
                        run_success=fallback_run_success,
                        summary=fallback_summary,
                        code=fallback_code,
                        stdout=str(fallback_result.get("stdout") or ""),
                        stderr=str(fallback_result.get("stderr") or ""),
                        artifacts=[str(name) for name in fallback_result.get("artifacts") or []],
                        structured_result=fallback_structured_result,
                        schema_valid=fallback_schema_valid,
                    )

                if _prefer_fallback_repair_candidate(
                    structured_result,
                    repair_findings,
                    fallback_schema_valid,
                    fallback_structured_result,
                    fallback_findings,
                ):
                    stderr_parts = [stderr_text]
                    if repair_reason:
                        stderr_parts.append(f"Retried with fallback solver after auto-check: {repair_reason}")
                    fallback_stderr = str(fallback_result.get("stderr") or "")
                    if fallback_stderr:
                        stderr_parts.append(f"Fallback stderr: {fallback_stderr}")
                    if fallback_schema_error:
                        stderr_parts.append(f"Fallback schema validation failed: {fallback_schema_error}")
                    stderr_text = "\n".join(part for part in stderr_parts if part).strip()
                    result = fallback_result
                    run_success = fallback_run_success
                    schema_valid = fallback_schema_valid
                    structured_result = fallback_structured_result
                    schema_error = fallback_schema_error
                    summary = f"{fallback_summary} Retried automatically after solver adequacy checks failed."
                    code = fallback_code
                    repair_findings = fallback_findings
                    current_filename = f"solver_{index}_fallback.py"

            if repair_findings:
                repair_reason = _summarize_repair_findings(repair_findings)
                if repair_reason:
                    stderr_text = (stderr_text + f"\nAuto-check flagged incomplete solver result: {repair_reason}").strip()
                structured_result = _downgrade_weak_result(structured_result, repair_findings)

            if not run_success and not structured_result:
                structured_result = {
                    "subproblem_title": subproblem.title,
                    "status": "failed",
                    "method": subproblem.analysis.chosen_method or "unknown",
                    "objective": subproblem.analysis.objective or "",
                    "assumptions": subproblem.analysis.assumptions,
                    "constraints": subproblem.analysis.constraints,
                    "result_summary": "Execution failed before a structured result was produced.",
                    "evidence": ["python_exec returned a non-zero exit status"],
                    "numeric_results": {},
                    "figure_titles": [],
                    "artifacts": [str(name) for name in result.get("artifacts") or []],
                    "next_steps": ["Inspect stderr and generated code before retrying."],
                }

            if structured_result:
                structured_result = _enrich_structured_result(
                    structured_result=structured_result,
                    run_success=run_success,
                    schema_valid=schema_valid,
                    stderr=stderr_text,
                    artifacts=[str(name) for name in result.get("artifacts") or []],
                    script_name=current_filename,
                    repair_findings=repair_findings,
                )

            solver_run = SolverRun(
                subproblem_title=subproblem.title,
                success=run_success and schema_valid and structured_result.get("status") in {"ok", "partial"},
                summary=summary,
                code=code,
                stdout=str(result.get("stdout") or ""),
                stderr=(stderr_text + (f"\nSchema validation failed: {schema_error}" if schema_error else "")).strip(),
                artifacts=[str(name) for name in result.get("artifacts") or []],
                structured_result=structured_result,
                schema_valid=schema_valid,
            )
            state.solver_runs.append(solver_run)
            structured_results.append(structured_result)
            state.artifacts.extend(_load_solver_artifacts(str(result.get("run_dir") or ""), solver_run.artifacts))

        state.results["structured_solver_results"] = structured_results
        state.results["status"] = _overall_solver_status(state.solver_runs)
        state.results["solver_summary"] = _summarize_solver_runs(state.solver_runs)
        state.results["solved_subproblems"] = [
            run.subproblem_title
            for run in state.solver_runs
            if run.schema_valid and run.structured_result.get("status") == "ok"
        ]
        state.results["partial_subproblems"] = [
            run.subproblem_title
            for run in state.solver_runs
            if run.schema_valid and run.structured_result.get("status") == "partial"
        ]
        state = SolveSkill().run(state, tools)
        memory.set_agent_json(
            self.name,
            "solver_result",
            {
                "status": state.results.get("status"),
                "summary": state.results.get("solver_summary"),
                "runs": _solver_runs_payload(state),
            },
        )
        memory.append_event("agent", self.name, "done", {"stage": state.stage})
        return state


@dataclass(frozen=True)
class ReviewAgent:
    name: str = "review"

    def run(self, state: TaskState, tools: ToolRegistry, memory: MemoryStore) -> TaskState:
        state = ValidateSkill().run(state, tools)

        findings = build_structural_review_findings(state)

        review_notes = list(state.results.get("review_notes", []))
        verification_summary = build_verification_summary(state)
        report_sources = build_report_sources(state)
        findings.extend(build_verification_findings(state, verification_summary, report_sources))
        findings = dedupe_findings(findings)
        if findings:
            review_notes.append(f"Identified {len(findings)} review findings.")
        else:
            review_notes.append("No major structural issues were detected.")

        state.results["review_findings"] = findings
        state.results["review_notes"] = review_notes
        state.results["verification_summary"] = verification_summary
        state.results["report_sources"] = report_sources
        if state.report_md is None:
            state.results["reviewed_solution"] = True
            state.stage = "report"
        else:
            state.results["report_checks"] = _required_report_sections()
            state.results["final_review_done"] = not has_blocking_review_findings(findings)
            state.stage = "done"

        memory.set_agent_json(
            self.name,
            "review",
            {
                "checks": state.results.get("checks", []),
                "notes": review_notes,
                "report_checks": state.results.get("report_checks", []),
                "findings": findings,
            },
        )
        memory.append_event("agent", self.name, "done", {"stage": state.stage})
        return state


@dataclass(frozen=True)
class WritingAgent:
    name: str = "writing"

    def run(self, state: TaskState, tools: ToolRegistry, memory: MemoryStore) -> TaskState:
        cfg = load_llm_config("WRITING")
        if cfg is not None:
            llm = build_llm(cfg)
            try:
                report = llm.chat(
                    [
                        Message(role="system", content=render_prompt("writing_system")),
                        Message(
                            role="user",
                            content=render_prompt(
                                "writing_user",
                                problem_text=state.problem_text,
                                retrieval_context=_retrieval_prompt_context(
                                    state,
                                    query=state.problem_text,
                                    limit=6,
                                ),
                                subproblems_json=json.dumps(_subproblems_payload(state), ensure_ascii=False, indent=2),
                                solver_runs_json=json.dumps(_solver_runs_payload(state), ensure_ascii=False, indent=2),
                                review_findings_json=json.dumps(
                                    state.results.get("review_findings", []),
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                            ),
                        ),
                    ],
                    temperature=0.2,
                )
                state.report_md = inject_figure_titles(stabilize_report_markdown(report.strip(), state), state)
            except Exception as exc:
                memory.set_agent_json(self.name, "llm_error", {"error": str(exc)})
                memory.append_event("agent", self.name, "llm_error", {"error": str(exc)})
                state = ReportSkill().run(state, tools)
        else:
            state = ReportSkill().run(state, tools)

        if state.report_md is not None:
            state.report_md = inject_figure_titles(stabilize_report_markdown(state.report_md, state), state)
            memory.set_shared("report_md", state.report_md)
            state.stage = "review"
        memory.append_event("agent", self.name, "done", {"stage": state.stage})
        return state

