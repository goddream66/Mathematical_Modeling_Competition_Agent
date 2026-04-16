from __future__ import annotations
import json
import re
from pathlib import Path

context = {
  "problem_text": "Problem 1: forecast demand for the next 5 days using values 10 12 15 18 20.\nProblem 2: optimize cost under budget 100 with candidate costs 25 40 70.\nProblem 3: find a path with distances 9 4 7 3.\nProblem 4: evaluate alternatives with scores 80 76 91.",
  "clarifications": [
    "Problem 4: what are the hard and soft constraints?"
  ],
  "subproblem_index": 3,
  "subproblem": {
    "title": "Problem 3",
    "text": "find a path with distances 9 4 7 3.",
    "analysis": {
      "task_types": [
        "路径/网络"
      ],
      "candidate_models": [
        "最短路径模型",
        "最小费用流",
        "车辆路径问题"
      ],
      "solution_plan": [
        "先明确输入、输出、约束和评价指标，避免模型目标漂移。",
        "先抽象成图结构，明确节点、边和权重。",
        "根据目标选择最短路、最小费用流或车辆路径模型。",
        "验证容量、时间窗和路径连通性等业务约束。"
      ],
      "key_variables": [
        "节点集合",
        "边权重",
        "路径选择变量"
      ],
      "needed_data": [
        "节点和边信息",
        "距离、时间或费用矩阵"
      ],
      "evaluation": [
        "检查假设是否合理、变量定义是否一致。",
        "比较总路径长度、总成本或准时率。"
      ],
      "notes": [
        "先把题目里的变量、单位、边界条件统一。",
        "避免在没有数据支撑时直接给出数值结论。"
      ],
      "objective": "在网络结构约束下找到最优路径或调度方案。",
      "constraints": [
        "需要验证连通性、容量或时间窗约束。"
      ],
      "assumptions": [
        "变量定义清晰且可以被观测、估计或求解。",
        "原始题面没有说明的外部环境在分析周期内保持相对稳定。"
      ],
      "deliverables": [
        "结构化建模思路",
        "关键公式或算法流程",
        "可复核的结论说明",
        "路径或调度方案"
      ],
      "formulation_steps": [
        "目标定义：在网络结构约束下找到最优路径或调度方案。",
        "约束梳理：需要验证连通性、容量或时间窗约束。",
        "把问题映射到图模型并定义节点、边和权重。"
      ],
      "chosen_method": "最短路径模型",
      "confidence": 0.75
    }
  },
  "all_subproblems": [
    {
      "title": "Problem 1",
      "text": "forecast demand for the next 5 days using values 10 12 15 18 20.",
      "analysis": {
        "task_types": [
          "预测/拟合"
        ],
        "candidate_models": [
          "线性/非线性回归",
          "ARIMA/Prophet",
          "灰色预测 GM(1,1)"
        ],
        "solution_plan": [
          "先明确输入、输出、约束和评价指标，避免模型目标漂移。",
          "整理历史数据并检查缺失、异常值和单位一致性。",
          "先建立基线模型，再与更复杂模型做对比。",
          "使用误差指标和回测结果评估预测稳定性。"
        ],
        "key_variables": [
          "时间索引",
          "目标变量",
          "解释变量"
        ],
        "needed_data": [
          "历史观测数据",
          "外部影响因素或特征变量"
        ],
        "evaluation": [
          "检查假设是否合理、变量定义是否一致。",
          "使用 MAE、RMSE、MAPE 等误差指标。",
          "进行回测或验证集评估。"
        ],
        "notes": [
          "先把题目里的变量、单位、边界条件统一。",
          "避免在没有数据支撑时直接给出数值结论。"
        ],
        "objective": "建立预测模型并给出可解释的误差评估。",
        "constraints": [
          "训练与验证数据划分方式需要保持时序一致。"
        ],
        "assumptions": [
          "变量定义清晰且可以被观测、估计或求解。",
          "原始题面没有说明的外部环境在分析周期内保持相对稳定。",
          "历史数据对未来具有一定代表性。"
        ],
        "deliverables": [
          "结构化建模思路",
          "关键公式或算法流程",
          "可复核的结论说明",
          "预测结果与误差分析"
        ],
        "formulation_steps": [
          "目标定义：建立预测模型并给出可解释的误差评估。",
          "约束梳理：训练与验证数据划分方式需要保持时序一致。",
          "构建特征和时间索引，给出训练、验证和预测流程。"
        ],
        "chosen_method": "线性/非线性回归",
        "confidence": 0.75
      }
    },
    {
      "title": "Problem 2",
      "text": "optimize cost under budget 100 with candidate costs 25 40 70.",
      "analysis": {
        "task_types": [
          "优化/决策"
        ],
        "candidate_models": [
          "线性规划",
          "整数规划/混合整数规划",
          "多目标优化"
        ],
        "solution_plan": [
          "先明确输入、输出、约束和评价指标，避免模型目标漂移。",
          "把文字规则转成决策变量、目标函数和约束条件。",
          "区分连续变量、整数变量和 0-1 变量。",
          "求解后做可行性检查和敏感性分析。"
        ],
        "key_variables": [
          "决策变量",
          "目标函数值",
          "约束边界"
        ],
        "needed_data": [
          "成本、收益或资源参数",
          "业务约束与上限"
        ],
        "evaluation": [
          "检查假设是否合理、变量定义是否一致。",
          "检查解的可行性和边界情况。",
          "做敏感性分析。"
        ],
        "notes": [
          "先把题目里的变量、单位、边界条件统一。",
          "避免在没有数据支撑时直接给出数值结论。"
        ],
        "objective": "构建目标函数并求得最优决策方案。",
        "constraints": [
          "需要明确资源上限、容量约束和业务规则。"
        ],
        "assumptions": [
          "变量定义清晰且可以被观测、估计或求解。",
          "原始题面没有说明的外部环境在分析周期内保持相对稳定。",
          "成本、收益或资源参数在求解区间内可视为已知。"
        ],
        "deliverables": [
          "结构化建模思路",
          "关键公式或算法流程",
          "可复核的结论说明",
          "最优方案与敏感性分析"
        ],
        "formulation_steps": [
          "目标定义：构建目标函数并求得最优决策方案。",
          "约束梳理：需要明确资源上限、容量约束和业务规则。",
          "把目标与约束写成线性规划、整数规划或多目标优化模型。"
        ],
        "chosen_method": "线性规划",
        "confidence": 0.75
      }
    },
    {
      "title": "Problem 3",
      "text": "find a path with distances 9 4 7 3.",
      "analysis": {
        "task_types": [
          "路径/网络"
        ],
        "candidate_models": [
          "最短路径模型",
          "最小费用流",
          "车辆路径问题"
        ],
        "solution_plan": [
          "先明确输入、输出、约束和评价指标，避免模型目标漂移。",
          "先抽象成图结构，明确节点、边和权重。",
          "根据目标选择最短路、最小费用流或车辆路径模型。",
          "验证容量、时间窗和路径连通性等业务约束。"
        ],
        "key_variables": [
          "节点集合",
          "边权重",
          "路径选择变量"
        ],
        "needed_data": [
          "节点和边信息",
          "距离、时间或费用矩阵"
        ],
        "evaluation": [
          "检查假设是否合理、变量定义是否一致。",
          "比较总路径长度、总成本或准时率。"
        ],
        "notes": [
          "先把题目里的变量、单位、边界条件统一。",
          "避免在没有数据支撑时直接给出数值结论。"
        ],
        "objective": "在网络结构约束下找到最优路径或调度方案。",
        "constraints": [
          "需要验证连通性、容量或时间窗约束。"
        ],
        "assumptions": [
          "变量定义清晰且可以被观测、估计或求解。",
          "原始题面没有说明的外部环境在分析周期内保持相对稳定。"
        ],
        "deliverables": [
          "结构化建模思路",
          "关键公式或算法流程",
          "可复核的结论说明",
          "路径或调度方案"
        ],
        "formulation_steps": [
          "目标定义：在网络结构约束下找到最优路径或调度方案。",
          "约束梳理：需要验证连通性、容量或时间窗约束。",
          "把问题映射到图模型并定义节点、边和权重。"
        ],
        "chosen_method": "最短路径模型",
        "confidence": 0.75
      }
    },
    {
      "title": "Problem 4",
      "text": "evaluate alternatives with scores 80 76 91.",
      "analysis": {
        "task_types": [
          "评价/权重"
        ],
        "candidate_models": [
          "AHP",
          "熵权法",
          "TOPSIS"
        ],
        "solution_plan": [
          "先明确输入、输出、约束和评价指标，避免模型目标漂移。",
          "建立指标体系并标明正向、逆向指标。",
          "选择 AHP、熵权或 TOPSIS 形成综合评价。",
          "检查权重稳定性和排序鲁棒性。"
        ],
        "key_variables": [
          "指标值",
          "指标权重",
          "综合得分"
        ],
        "needed_data": [
          "指标明细数据",
          "指标方向说明"
        ],
        "evaluation": [
          "检查假设是否合理、变量定义是否一致。",
          "检查排序稳定性和权重鲁棒性。"
        ],
        "notes": [
          "先把题目里的变量、单位、边界条件统一。",
          "避免在没有数据支撑时直接给出数值结论。"
        ],
        "objective": "构建评价体系并形成可信的排序结果。",
        "constraints": [],
        "assumptions": [
          "变量定义清晰且可以被观测、估计或求解。",
          "原始题面没有说明的外部环境在分析周期内保持相对稳定。"
        ],
        "deliverables": [
          "结构化建模思路",
          "关键公式或算法流程",
          "可复核的结论说明",
          "评价排序与权重解释"
        ],
        "formulation_steps": [
          "目标定义：构建评价体系并形成可信的排序结果。",
          "先标准化指标，再进行赋权与综合评分。"
        ],
        "chosen_method": "AHP",
        "confidence": 0.75
      }
    }
  ],
  "input_data": {},
  "retrieval": {
    "provider": "none",
    "query": "Problem 1: forecast demand for the next 5 days using values 10 12 15 18 20.\nProblem 2: optimize cost under budget 100 with candidate costs 25 40 70.\nProblem 3: find a path with distances 9 4 7 3.\nProblem 4: evaluate alternatives with scores 80 76 91.",
    "chunks": []
  },
  "model": {
    "assumptions": [
      "变量定义清晰且可以被观测、估计或求解。",
      "原始题面没有说明的外部环境在分析周期内保持相对稳定。",
      "历史数据对未来具有一定代表性。",
      "成本、收益或资源参数在求解区间内可视为已知。"
    ],
    "constraints": [
      "训练与验证数据划分方式需要保持时序一致。",
      "需要明确资源上限、容量约束和业务规则。",
      "需要验证连通性、容量或时间窗约束。"
    ],
    "method_candidates": [
      "线性/非线性回归",
      "ARIMA/Prophet",
      "灰色预测 GM(1,1)",
      "线性规划",
      "整数规划/混合整数规划",
      "多目标优化",
      "最短路径模型",
      "最小费用流"
    ],
    "chosen_method": "线性/非线性回归",
    "formulation_outline": [
      "目标定义：建立预测模型并给出可解释的误差评估。",
      "约束梳理：训练与验证数据划分方式需要保持时序一致。",
      "构建特征和时间索引，给出训练、验证和预测流程。",
      "目标定义：构建目标函数并求得最优决策方案。",
      "约束梳理：需要明确资源上限、容量约束和业务规则。",
      "把目标与约束写成线性规划、整数规划或多目标优化模型。",
      "目标定义：在网络结构约束下找到最优路径或调度方案。",
      "约束梳理：需要验证连通性、容量或时间窗约束。",
      "把问题映射到图模型并定义节点、边和权重。",
      "目标定义：构建评价体系并形成可信的排序结果。"
    ],
    "evidence_gaps": [
      "历史观测数据",
      "外部影响因素或特征变量",
      "成本、收益或资源参数",
      "业务约束与上限",
      "节点和边信息",
      "距离、时间或费用矩阵",
      "指标明细数据",
      "指标方向说明"
    ]
  }
}
subproblem = context["subproblem"]
analysis = subproblem["analysis"]
tables = [table for table in context.get("input_data", {}).get("tables", []) if table.get("kind") == "table"]
text = subproblem["text"] or context["problem_text"]
numbers = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]
table_name = None
source_column = None
target_column = None
weight_column = None
node_set = set()
edge_rows = []

for table in tables:
    lower_map = {str(column).lower(): str(column) for column in table.get("columns", [])}
    source_column = lower_map.get("source") or lower_map.get("from") or lower_map.get("start")
    target_column = lower_map.get("target") or lower_map.get("to") or lower_map.get("end")
    weight_column = lower_map.get("weight") or lower_map.get("distance") or lower_map.get("cost")
    if source_column and target_column and weight_column:
        for row in table.get("rows", []):
            if isinstance(row.get(weight_column), (int, float)) and not isinstance(row.get(weight_column), bool):
                edge_rows.append((str(row.get(source_column)), str(row.get(target_column)), float(row.get(weight_column))))
                node_set.add(str(row.get(source_column)))
                node_set.add(str(row.get(target_column)))
        if edge_rows:
            table_name = table.get("name", "table")
            break

weights = [row[2] for row in edge_rows] if edge_rows else [float(x) for x in numbers if x > 0]
graph_node_count = len(node_set) if node_set else 0
edge_count = len(edge_rows) if edge_rows else len(weights)
average_edge_weight = float(sum(weights) / len(weights)) if weights else 0.0
max_edge_weight = float(max(weights)) if weights else 0.0
min_edge_weight = float(min(weights)) if weights else 0.0
distance_reference_sum = float(sum(weights)) if weights else 0.0
cumulative_weights = []
running = 0.0
for value in weights[:12]:
    running += float(value)
    cumulative_weights.append(round(running, 4))
status = "ok" if weights else "partial"

weight_title = f"{subproblem['title']}: edge weight diagnostics"
cumulative_title = f"{subproblem['title']}: cumulative distance diagnostics"
weight_file = "path_weight_profile.svg"
cumulative_file = "path_cumulative_weight.svg"

def _write_bar_chart(path):
    values = list(weights[:8]) or [0.0]
    width = 720
    height = 420
    left = 70
    top = 60
    bottom = 60
    chart_h = height - top - bottom
    max_value = max(values + [1.0])
    step = 70
    bars = []
    labels = []
    for index, value in enumerate(values):
        x = left + index * step
        bar_h = chart_h * float(value) / max_value
        y = top + chart_h - bar_h
        bars.append(f"<rect x='{x}' y='{y:.1f}' width='32' height='{bar_h:.1f}' fill='#0f766e' rx='4'/>")
        labels.append(f"<text x='{x + 16}' y='380' font-size='12' text-anchor='middle'>e{index + 1}</text>")
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{width/2:.1f}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{weight_title}</text>
<line x1='{left-10}' y1='{height-bottom}' x2='{width-30}' y2='{height-bottom}' stroke='#111827' stroke-width='2'/>
{''.join(bars)}
{''.join(labels)}
</svg>"""
    Path(path).write_text(svg, encoding="utf-8")

def _write_line_chart(path):
    values = list(cumulative_weights) or [0.0]
    width = 720
    height = 420
    left = 70
    right = 50
    top = 60
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    ymin = min(values)
    ymax = max(values)
    if ymin == ymax:
        ymin -= 1.0
        ymax += 1.0
    def _xy(index, value, total):
        x = left + plot_w * index / max(total - 1, 1)
        y = top + plot_h * (1.0 - (float(value) - ymin) / (ymax - ymin))
        return x, y
    points = [_xy(i, values[i], len(values)) for i in range(len(values))]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points) if points else ""
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{width/2:.1f}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{cumulative_title}</text>
<line x1='{left}' y1='{height-bottom}' x2='{width-right}' y2='{height-bottom}' stroke='#111827' stroke-width='2'/>
<polyline points='{polyline}' fill='none' stroke='#2563eb' stroke-width='3'/>
</svg>"""
    Path(path).write_text(svg, encoding="utf-8")

_write_bar_chart(weight_file)
_write_line_chart(cumulative_file)

result = {
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "path_validation_template",
    "objective": analysis.get("objective") or "Validate network weight structure and generate path diagnostics without selecting a final route.",
    "assumptions": analysis.get("assumptions") or ["Detected numbers are treated as edge-weight evidence only."],
    "constraints": analysis.get("constraints") or ["The fallback template does not choose a final route or path algorithm for the LLM."],
    "result_summary": "Generated a path/network validation bundle without selecting a final route.",
    "evidence": [
        "template_used=path_validation_template",
        f"table_name={table_name or 'none'}",
        f"source_column={source_column or 'none'}",
        f"target_column={target_column or 'none'}",
        f"weight_column={weight_column or 'none'}",
        f"edge_count_estimate={edge_count}",
    ],
    "numeric_results": {
        "edge_count_estimate": edge_count,
        "graph_node_count": graph_node_count,
        "path_weight_mean": round(average_edge_weight, 4),
        "max_edge_weight": round(max_edge_weight, 4),
        "min_edge_weight": round(min_edge_weight, 4),
        "distance_reference_sum": round(distance_reference_sum, 4),
        "path_density_ratio": round(float(edge_count / max(graph_node_count, 1)), 4) if edge_count else 0.0,
    },
    "figure_titles": [weight_title, cumulative_title],
    "artifacts": ["result.json", "path_validation.json", weight_file, cumulative_file],
    "verification_checks": [
        f"weight_detection:{'passed' if weights else 'failed'}",
        f"explicit_graph_edges:{'passed' if edge_rows else 'missing'}",
        f"multi_chart_generation:{'passed' if weights else 'limited'}",
    ],
    "constraint_checks": [
        f"positive_weight_check:{'passed' if all(value >= 0 for value in weights) else 'failed'}",
        f"graph_context_available:{'passed' if edge_rows else 'limited'}",
    ],
    "error_metrics": {
        "weight_range": round(max_edge_weight - min_edge_weight, 4) if weights else 0.0,
    },
    "robustness_checks": [
        f"average_edge_weight={round(average_edge_weight, 4)}",
        f"cumulative_distance_last={round(cumulative_weights[-1], 4) if cumulative_weights else 0.0}",
    ],
    "suspicious_points": (
        (["graph_structure_missing"] if not edge_rows else [])
        + (["nonpositive_weights_detected"] if any(value <= 0 for value in weights) else [])
    ),
    "final_verdict": "validated" if weights else "needs_review",
    "plot_code_hint": "See path_weight_profile.svg and path_cumulative_weight.svg generation in solver_*.py.",
    "next_steps": [
        "Run the LLM-proposed routing or shortest-path algorithm and compare it against these structural diagnostics.",
        "Provide an explicit graph, adjacency matrix, or constraints before trusting a final route.",
    ],
}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("path_validation.json").write_text(
    json.dumps(
        {
            "weights": weights[:20],
            "edge_count_estimate": edge_count,
            "graph_node_count": graph_node_count,
            "distance_reference_sum": distance_reference_sum,
            "cumulative_weights": cumulative_weights,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))