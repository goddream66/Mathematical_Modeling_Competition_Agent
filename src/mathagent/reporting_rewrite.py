from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .state import TaskState


@dataclass(frozen=True)
class ReportSectionSpec:
    key: str
    title: str
    aliases: tuple[str, ...]

    @property
    def heading(self) -> str:
        return f"# {self.title}"


REPORT_SECTION_SPECS: tuple[ReportSectionSpec, ...] = (
    ReportSectionSpec("abstract", "摘要", ("abstract", "summary", "鎽樿")),
    ReportSectionSpec(
        "problem",
        "问题重述",
        ("problem", "statement", "problem_statement", "闂", "闂閲嶈堪", "棰樼洰"),
    ),
    ReportSectionSpec(
        "analysis",
        "子问题分析与方法选择",
        ("analysis", "method", "methods", "瀛愰棶棰樺垎鏋愪笌鏂规硶閫夋嫨", "鍒嗘瀽", "鏂规硶"),
    ),
    ReportSectionSpec(
        "modeling",
        "模型假设与符号说明",
        ("model", "modeling", "assumptions", "symbols", "妯″瀷", "鍋囪", "绗﹀彿"),
    ),
    ReportSectionSpec(
        "solving",
        "求解与实验",
        ("solve", "solving", "experiment", "experiments", "姹傝В", "瀹為獙"),
    ),
    ReportSectionSpec(
        "results",
        "结果与分析",
        ("result", "results", "finding", "findings", "缁撴灉", "鍒嗘瀽"),
    ),
    ReportSectionSpec(
        "review",
        "审稿提示",
        ("review", "checks", "findings", "瀹＄", "鎻愮ず"),
    ),
    ReportSectionSpec(
        "conclusion",
        "结论与后续工作",
        ("conclusion", "conclusions", "next", "discussion", "缁撹", "鍚庣画"),
    ),
)

_SECTION_BY_KEY = {spec.key: spec for spec in REPORT_SECTION_SPECS}
_SECTION_ALIASES = {
    alias.lower(): spec.key
    for spec in REPORT_SECTION_SPECS
    for alias in (spec.key, spec.title, *spec.aliases)
}

_PLACEHOLDER_TEXT_MARKERS = (
    "pending_constraint",
    "formal constraints still need to be written explicitly",
    "constraints still need to be written",
    "constraint still needs to be written",
    "placeholder",
    "todo",
    "tbd",
)

_RESULT_KEYWORDS = (
    "forecast",
    "predict",
    "estimate",
    "objective",
    "cost",
    "profit",
    "score",
    "weight",
    "rank",
    "distance",
    "path",
    "ratio",
    "error",
    "mae",
    "rmse",
    "mape",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "residual",
    "stability",
    "value",
    "time",
    "rate",
    "loss",
)

_COUNTER_KEYWORDS = (
    "count",
    "num",
    "number",
    "index",
    "idx",
    "measurement",
    "sample",
    "point",
    "history",
    "historical",
)

_GENERATED_MARKERS = (
    "## Structured Subproblem Alignment",
    "## Structured Solver Runs",
    "## Structured Results Alignment",
    "## Review Conclusion",
    "## 执行状态摘要",
    "## 结构化建模核验",
    "## 执行与验证说明",
    "## 结构化结果摘要",
    "## 审稿结论概览",
    "## 交付判断",
)


def available_report_sections() -> list[dict[str, str]]:
    return [{"key": spec.key, "title": spec.title} for spec in REPORT_SECTION_SPECS]


def required_report_titles() -> list[str]:
    return [
        _SECTION_BY_KEY["abstract"].heading,
        _SECTION_BY_KEY["problem"].heading,
        _SECTION_BY_KEY["analysis"].heading,
        _SECTION_BY_KEY["modeling"].heading,
        _SECTION_BY_KEY["solving"].heading,
        _SECTION_BY_KEY["results"].heading,
        _SECTION_BY_KEY["conclusion"].heading,
    ]


def resolve_report_sections(values: list[str] | None) -> list[str]:
    if not values:
        return []

    resolved: list[str] = []
    unknown: list[str] = []
    for raw in values:
        for token in _split_section_tokens(raw):
            lowered = token.lower()
            if lowered == "all":
                return []
            key = _SECTION_ALIASES.get(lowered)
            if key is None:
                unknown.append(token)
                continue
            if key not in resolved:
                resolved.append(key)
    if unknown:
        options = ", ".join(f"{spec.key}({spec.title})" for spec in REPORT_SECTION_SPECS)
        raise ValueError(f"Unknown report section: {', '.join(unknown)}. Available: {options}")
    return resolved


def select_report_sections(markdown: str, section_keys: list[str] | None) -> str:
    if not markdown.strip() or not section_keys:
        return markdown

    sections = _split_markdown_sections(markdown)
    if not sections:
        return markdown

    selected_blocks: list[str] = []
    wanted_keys = {key for key in section_keys if key in _SECTION_BY_KEY}
    for title, block in sections:
        resolved_key = _section_key_from_title(title)
        if resolved_key in wanted_keys:
            selected_blocks.append(block.rstrip())
    return "\n\n".join(selected_blocks).strip() or markdown


def extract_report_section(markdown: str, section_key: str) -> str:
    if not markdown.strip() or section_key not in _SECTION_BY_KEY:
        return ""

    matched_blocks: list[str] = []
    for title, block in _split_markdown_sections(markdown):
        if _section_key_from_title(title) == section_key:
            matched_blocks.append(block.rstrip())
    return "\n\n".join(matched_blocks).strip()


def inject_figure_titles(markdown: str, state: TaskState) -> str:
    entries: list[tuple[str, list[str]]] = []
    for run in state.solver_runs:
        titles = [str(item).strip() for item in run.structured_result.get("figure_titles", []) if str(item).strip()]
        if titles:
            entries.append((run.subproblem_title, titles))

    if not entries:
        return markdown

    block_lines = ["## 图表标题", "后端生成的图表标题如下："]
    for subproblem_title, titles in entries:
        block_lines.append(f"### {subproblem_title}")
        for index, title in enumerate(titles, start=1):
            block_lines.append(f"- 图{index}: {title}")
        block_lines.append("")
    block = "\n".join(block_lines).strip()

    sections = _split_markdown_sections(markdown)
    if not sections:
        return (markdown.rstrip() + "\n\n" + block).strip()

    updated_blocks: list[str] = []
    inserted = False
    for title, section_block in sections:
        if not inserted and _section_key_from_title(title) == "results":
            if "## 图表标题" in section_block:
                updated_blocks.append(section_block.rstrip())
            else:
                updated_blocks.append(section_block.rstrip() + "\n\n" + block)
            inserted = True
        else:
            updated_blocks.append(section_block.rstrip())

    if not inserted:
        updated_blocks.append(f"{_SECTION_BY_KEY['results'].heading}\n\n{block}".strip())
    return "\n\n".join(part for part in updated_blocks if part).strip()


def render_fallback_report(state: TaskState) -> str:
    report = "\n\n".join(
        [
            f"{_SECTION_BY_KEY['abstract'].heading}\n{_build_base_abstract(state)}",
            f"{_SECTION_BY_KEY['problem'].heading}\n{state.problem_text.strip() or '未提供题面。'}",
            _SECTION_BY_KEY["analysis"].heading,
            f"{_SECTION_BY_KEY['modeling'].heading}\n{_build_modeling_section_fallback(state)}",
            _SECTION_BY_KEY["solving"].heading,
            _SECTION_BY_KEY["results"].heading,
            _SECTION_BY_KEY["conclusion"].heading,
        ]
    )
    return stabilize_report_markdown(report, state)


def stabilize_report_markdown(markdown: str, state: TaskState) -> str:
    report = _strip_generated_subsections(markdown.strip())
    if not report:
        report = f"{_SECTION_BY_KEY['abstract'].heading}\n{_build_base_abstract(state)}"

    report = _upsert_report_section(report, _SECTION_BY_KEY["abstract"].heading, _build_abstract_guard_block(state), "## 执行状态摘要")
    report = _upsert_report_section(report, _SECTION_BY_KEY["problem"].heading, state.problem_text.strip() or "未提供题面。", "")
    report = _upsert_report_section(report, _SECTION_BY_KEY["analysis"].heading, _build_analysis_alignment_block(state), "## 结构化建模核验")
    report = _upsert_report_section(report, _SECTION_BY_KEY["modeling"].heading, _build_modeling_section_fallback(state), "")
    report = _upsert_report_section(report, _SECTION_BY_KEY["solving"].heading, _build_solving_alignment_block(state), "## 执行与验证说明")
    report = _upsert_report_section(report, _SECTION_BY_KEY["results"].heading, _build_results_alignment_block(state), "## 结构化结果摘要")

    findings = state.results.get("review_findings", [])
    if findings:
        report = _upsert_report_section(report, _SECTION_BY_KEY["review"].heading, _build_review_section_block(state), "## 审稿结论概览")

    report = _upsert_report_section(report, _SECTION_BY_KEY["conclusion"].heading, _build_conclusion_alignment_block(state), "## 交付判断")
    return report.strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _is_placeholder_text(value: Any) -> bool:
    text = _clean_text(value).lower()
    if not text:
        return True
    return any(marker in text for marker in _PLACEHOLDER_TEXT_MARKERS)


def _clean_constraints(values: Any) -> list[str]:
    return [item for item in _string_list(values) if not _is_placeholder_text(item)]


def _normalize_method_name(value: Any) -> str:
    text = _clean_text(value).lower().replace("/", " ").replace("-", " ").replace("_", " ")
    return " ".join(text.split())


def _methods_materially_differ(planned: Any, executed: Any) -> bool:
    planned_text = _normalize_method_name(planned)
    executed_text = _normalize_method_name(executed)
    if not planned_text or not executed_text or planned_text == executed_text:
        return False
    return planned_text not in executed_text and executed_text not in planned_text


def _build_base_abstract(state: TaskState) -> str:
    provisional_runs = _provisional_run_count(state)
    if provisional_runs:
        return "本文汇总了题目拆解、建模方案与程序化验证结果，但部分子问题仍处于待复核状态，因此下文会将相关结果标记为暂定结论。"
    if state.solver_runs:
        return "本文汇总了题目拆解、模型设计、求解验证与审稿检查，尽量让每个结论都绑定到结构化证据。"
    return "本文给出题目重述、建模思路与待补充的求解计划，当前尚未产生稳定的程序化结果。"


def _build_abstract_guard_block(state: TaskState) -> str:
    warnings = _collect_global_execution_warnings(state)
    lines = ["## 执行状态摘要", f"- 总体求解状态: {state.results.get('status', 'unknown')}"]
    if warnings:
        lines.append("- 当前报告含有回退执行、超时恢复或待复核结果，正文中的相关结论应视为暂定结论。")
        for item in warnings[:4]:
            lines.append(f"- 执行限制: {item}")
    else:
        lines.append("- 当前未检测到明显的回退执行或超时恢复标记。")
    return "\n".join(lines)


def _build_modeling_section_fallback(state: TaskState) -> str:
    lines: list[str] = []
    assumptions = _string_list(state.model.assumptions)
    lines.extend(_render_bullets(assumptions, empty_text="尚未提炼出全局建模假设。"))
    lines.extend(["", "## 建模主线"])
    outline = _string_list(state.model.formulation_outline)
    lines.extend(_render_bullets(outline, empty_text="当前仅适合先完成子问题级别的结构化建模与验证。"))
    lines.extend(["", "## 全局约束"])
    constraints = _clean_constraints(state.model.constraints)
    lines.extend(_render_bullets(constraints, empty_text="全局约束尚未完整显式化，正式建模前需要补齐。"))
    return "\n".join(lines).strip()


def _build_analysis_alignment_block(state: TaskState) -> str:
    lines = ["## 结构化建模核验"]
    run_by_title = {run.subproblem_title: run for run in state.solver_runs}
    if not state.subproblems:
        lines.append("- 尚未生成子问题拆解。")
        return "\n".join(lines)

    for subproblem in state.subproblems:
        analysis = subproblem.analysis
        run = run_by_title.get(subproblem.title)
        executed_method = _clean_text((run.structured_result if run else {}).get("method"))
        lines.extend(
            [
                f"### {subproblem.title}",
                f"- 建模目标: {analysis.objective or '待明确'}",
                f"- 规划方法: {analysis.chosen_method or '待明确'}",
            ]
        )
        if executed_method:
            lines.append(f"- 实际执行方法: {executed_method}")
            if _methods_materially_differ(analysis.chosen_method, executed_method):
                lines.append("- 方法一致性: 建模阶段方法与实际执行方法不一致，需在正文中说明切换原因。")

        constraints = _clean_constraints(analysis.constraints)
        if constraints:
            lines.extend(f"- 约束: {item}" for item in constraints[:4])
        else:
            lines.append("- 约束状态: 约束尚未完整提炼，当前只能形成诊断性建模框架。")
        lines.append("")

    return "\n".join(lines).strip()


def _build_solving_alignment_block(state: TaskState) -> str:
    lines = ["## 执行与验证说明"]
    if not state.solver_runs:
        lines.append("- 尚未生成可执行求解结果。")
        return "\n".join(lines)

    for run in state.solver_runs:
        structured = run.structured_result
        warnings = _run_execution_warnings(run)
        lines.extend(
            [
                f"### {run.subproblem_title}",
                f"- 执行状态: {structured.get('status', 'unknown')}",
                f"- 最终判定: {structured.get('final_verdict', 'unknown') or 'unknown'}",
                f"- 结果摘要: {structured.get('result_summary', run.summary) or run.summary}",
            ]
        )
        if warnings:
            lines.extend(f"- 执行限制: {item}" for item in warnings[:3])
        plot_code_hint = _clean_text(structured.get("plot_code_hint"))
        if plot_code_hint:
            lines.append(f"- 绘图代码位置: {plot_code_hint}")
        figure_titles = _string_list(structured.get("figure_titles"))
        if figure_titles:
            lines.append(f"- 图表标题: {'；'.join(figure_titles[:3])}")
        lines.append("")

    return "\n".join(lines).strip()


def _build_results_alignment_block(state: TaskState) -> str:
    lines = ["## 结构化结果摘要"]
    if not state.solver_runs:
        lines.append("- 当前没有结构化结果可供分析。")
        return "\n".join(lines)

    subproblem_by_title = {subproblem.title: subproblem for subproblem in state.subproblems}
    for run in state.solver_runs:
        structured = run.structured_result
        subproblem = subproblem_by_title.get(run.subproblem_title)
        meaningful_numeric = _meaningful_numeric_results(structured.get("numeric_results"))
        evidence = _string_list(structured.get("evidence"))
        warnings = _run_execution_warnings(run)
        verdict = _clean_text(structured.get("final_verdict")) or "unknown"
        status = _clean_text(structured.get("status")) or "unknown"

        lines.append(f"### {run.subproblem_title}")
        lines.append(f"- 结果状态: {status} / {verdict}")
        lines.append(f"- 结构化摘要: {structured.get('result_summary', run.summary) or run.summary}")
        if meaningful_numeric:
            lines.append(f"- 关键指标: {_format_metrics_inline(meaningful_numeric)}")
        else:
            lines.append("- 定量结果: 当前只有空值、计数元数据或与任务无关的诊断字段，不能据此写成最终结论。")
        if evidence:
            lines.append(f"- 证据锚点: {'；'.join(evidence[:3])}")
        if _methods_materially_differ(getattr(getattr(subproblem, 'analysis', None), 'chosen_method', ''), structured.get('method')):
            lines.append("- 风险提示: 建模阶段方法与实际执行方法不一致，结果解释需要复核。")
        if not _available_constraints(subproblem, structured):
            lines.append("- 约束提示: 关键约束仍不完整，当前结果只能作为验证模板或中间结果。")
        if _is_run_provisional(run, subproblem):
            lines.append("- 结论等级: 该部分属于诊断性或暂定结果，不应直接当作最终竞赛答案提交。")
        if warnings:
            lines.append(f"- 执行限制: {'；'.join(warnings[:3])}")
        figure_titles = _string_list(structured.get("figure_titles"))
        if figure_titles:
            lines.append(f"- 图表引用: {'；'.join(figure_titles[:3])}")
        lines.append("")

    return "\n".join(lines).strip()


def _build_review_section_block(state: TaskState) -> str:
    findings = [item for item in state.results.get("review_findings", []) if isinstance(item, dict)]
    lines = ["## 审稿结论概览", f"- 审稿问题总数: {len(findings)}"]
    grouped: dict[str, list[dict[str, str]]] = {"high": [], "medium": [], "low": [], "info": []}
    for finding in findings:
        severity = _clean_text(finding.get("severity")).lower() or "info"
        grouped.setdefault(severity, []).append(finding)

    for severity, title in (("high", "高优先级"), ("medium", "中优先级"), ("low", "低优先级"), ("info", "提示信息")):
        bucket = grouped.get(severity, [])
        if not bucket:
            continue
        lines.extend(["", f"## {title}"])
        for finding in bucket:
            lines.append(f"- {finding.get('message', '')}")
            suggestion = _clean_text(finding.get("suggestion"))
            if suggestion:
                lines.append(f"- 建议: {suggestion}")
    return "\n".join(lines).strip()


def _build_conclusion_alignment_block(state: TaskState) -> str:
    solved = state.results.get("solved_subproblems", [])
    partial = state.results.get("partial_subproblems", [])
    lines = [
        "## 交付判断",
        f"- 已完成子问题: {', '.join(solved) if solved else '无'}",
        f"- 部分完成子问题: {', '.join(partial) if partial else '无'}",
        f"- 总体状态: {state.results.get('status', 'unknown')}",
    ]
    if _provisional_run_count(state):
        lines.append("- 当前版本更适合作为建模草稿和验证报告，不建议直接作为最终论文结论提交。")
    else:
        lines.append("- 当前版本已形成较稳定的结构化结果，但仍建议在提交前进行一次人工复核。")
    return "\n".join(lines).strip()


def _meaningful_numeric_results(value: Any) -> dict[str, float | int | str]:
    if not isinstance(value, dict):
        return {}
    meaningful: dict[str, float | int | str] = {}
    fallback: dict[str, float | int | str] = {}
    for raw_key, raw_value in value.items():
        key = _clean_text(raw_key)
        if not key:
            continue
        lowered = key.lower()
        if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
            if any(keyword in lowered for keyword in _RESULT_KEYWORDS):
                meaningful[key] = raw_value
            elif not any(keyword in lowered for keyword in _COUNTER_KEYWORDS):
                fallback[key] = raw_value
        else:
            clean_value = _clean_text(raw_value)
            if clean_value and any(keyword in lowered for keyword in _RESULT_KEYWORDS):
                meaningful[key] = clean_value
    return meaningful or dict(list(fallback.items())[:3])


def _available_constraints(subproblem: Any, structured_result: dict[str, Any]) -> list[str]:
    analysis_constraints = _clean_constraints(getattr(getattr(subproblem, "analysis", None), "constraints", []))
    if analysis_constraints:
        return analysis_constraints
    return _clean_constraints(structured_result.get("constraints"))


def _run_execution_warnings(run: Any) -> list[str]:
    text = "\n".join([_clean_text(getattr(run, "summary", "")), _clean_text(getattr(run, "stderr", ""))]).lower()
    warnings: list[str] = []
    if "generation failure" in text or "recovered from coding generation failure" in text:
        warnings.append("编码阶段发生过大模型生成失败，当前结果经过恢复流程。")
    if "retried with fallback solver" in text or "fallback solver" in text:
        warnings.append("求解过程中触发了 fallback 验证模板，结果可信度应降级处理。")
    if "timed out" in text or "timeout" in text:
        warnings.append("执行过程中出现超时或接近超时现象。")
    if _clean_text(getattr(run, "stderr", "")) and not warnings:
        warnings.append("执行阶段存在 stderr 输出，建议人工复核。")
    return warnings


def _collect_global_execution_warnings(state: TaskState) -> list[str]:
    seen: set[str] = set()
    warnings: list[str] = []
    for run in state.solver_runs:
        for item in _run_execution_warnings(run):
            if item not in seen:
                warnings.append(item)
                seen.add(item)
    return warnings


def _is_run_provisional(run: Any, subproblem: Any) -> bool:
    structured = getattr(run, "structured_result", {}) or {}
    status = _clean_text(structured.get("status")).lower()
    verdict = _clean_text(structured.get("final_verdict")).lower()
    if status in {"partial", "failed"} or verdict in {"needs_review", "failed"}:
        return True
    if _run_execution_warnings(run):
        return True
    if not _meaningful_numeric_results(structured.get("numeric_results")):
        return True
    return not _available_constraints(subproblem, structured)


def _provisional_run_count(state: TaskState) -> int:
    subproblem_by_title = {subproblem.title: subproblem for subproblem in state.subproblems}
    return sum(1 for run in state.solver_runs if _is_run_provisional(run, subproblem_by_title.get(run.subproblem_title)))


def _format_metrics_inline(metrics: dict[str, Any]) -> str:
    return "；".join(f"{key}={value}" for key, value in list(metrics.items())[:5])


def _render_bullets(items: list[str], *, empty_text: str = "暂无信息") -> list[str]:
    if not items:
        return [f"- {empty_text}"]
    return [f"- {item}" for item in items]


def _split_top_level_sections(markdown: str) -> list[list[str]]:
    if not markdown.strip():
        return []
    sections: list[list[str]] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            if current:
                sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)
    return sections


def _upsert_report_section(markdown: str, heading: str, content: str, marker: str) -> str:
    content = content.strip()
    if not content:
        return markdown.strip()

    sections = _split_top_level_sections(markdown)
    if not sections:
        return f"{heading}\n{content}".strip()

    updated_sections: list[str] = []
    inserted = False
    for section_lines in sections:
        section_text = "\n".join(section_lines).rstrip()
        if section_lines[0].strip() == heading:
            if marker and marker in section_text:
                updated_sections.append(section_text)
            else:
                if section_text.strip() == heading.strip():
                    updated_sections.append(f"{heading}\n{content}".strip())
                else:
                    updated_sections.append((section_text + "\n\n" + content).strip())
            inserted = True
        else:
            updated_sections.append(section_text)
    if not inserted:
        updated_sections.append(f"{heading}\n{content}".strip())
    return "\n\n".join(part for part in updated_sections if part).strip()


def _strip_generated_subsections(markdown: str) -> str:
    cleaned = markdown
    for marker in _GENERATED_MARKERS:
        pattern = re.compile(rf"(?ms)^\s*{re.escape(marker)}\n.*?(?=^\s*##\s|\Z)")
        cleaned = re.sub(pattern, "", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _split_section_tokens(raw: str) -> list[str]:
    return [token.strip() for token in raw.replace(",", " ").split() if token.strip()]


def _normalize_section_title(title: str) -> str:
    normalized = title.strip()
    normalized = re.sub(
        r"^(?:第\s*[0-9一二三四五六七八九十百零]+[章节部分篇]\s*|[0-9一二三四五六七八九十]+(?:\.[0-9]+)*\s*[.、:：\-\)]\s*)",
        "",
        normalized,
    )
    return normalized.strip()


def _section_key_from_title(title: str) -> str | None:
    normalized = _normalize_section_title(title).lower()
    candidates = (
        normalized,
        normalized.replace(" ", "_"),
        normalized.replace(" ", ""),
        normalized.replace("-", "_"),
    )
    for candidate in candidates:
        key = _SECTION_ALIASES.get(candidate)
        if key is not None:
            return key
    return None


def _split_markdown_sections(markdown: str) -> list[tuple[str, str]]:
    lines = markdown.splitlines()
    sections: list[tuple[str, str]] = []
    current_title = "__preface__"
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("# "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[2:].strip()
            current_lines = [line]
            continue
        current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections
