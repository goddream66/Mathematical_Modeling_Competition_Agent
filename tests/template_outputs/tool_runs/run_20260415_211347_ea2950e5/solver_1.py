from __future__ import annotations
import json
import math
import re
import statistics
from pathlib import Path

context = {
  "problem_text": "Problem 1: forecast demand for the next 5 days using values 10 12 15 18 20.\nProblem 2: optimize cost under budget 100 with candidate costs 25 40 70.\nProblem 3: find a path with distances 9 4 7 3.\nProblem 4: evaluate alternatives with scores 80 76 91.",
  "clarifications": [
    "Problem 4: what are the hard and soft constraints?"
  ],
  "subproblem_index": 1,
  "subproblem": {
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
horizon_match = re.search(r"(?:next|future|ahead|forecast|预测)\D*(\d+)", text, re.IGNORECASE)
forecast_horizon = int(horizon_match.group(1)) if horizon_match else 1

def _numeric_columns(table):
    columns = []
    for column in table.get("columns", []):
        if any(isinstance(row.get(column), (int, float)) and not isinstance(row.get(column), bool) for row in table.get("rows", [])):
            columns.append(column)
    return columns

def _choose_series():
    for table in tables:
        numeric_columns = _numeric_columns(table)
        if not numeric_columns:
            continue
        lower_map = {str(col).lower(): str(col) for col in numeric_columns}
        selected = None
        for name in ["value", "values", "demand", "sales", "quantity", "target", "y"]:
            if name in lower_map:
                selected = lower_map[name]
                break
        if selected is None:
            selected = numeric_columns[-1]
        values = [
            float(row[selected])
            for row in table.get("rows", [])
            if isinstance(row.get(selected), (int, float)) and not isinstance(row.get(selected), bool)
        ]
        if len(values) >= 2:
            return table.get("name", "table"), selected, values
    return None, None, []

table_name, selected_column, series = _choose_series()
if not series:
    series = list(numbers)
if horizon_match and series:
    horizon_value = float(forecast_horizon)
    removed = False
    filtered = []
    for value in series:
        if not removed and value == horizon_value:
            removed = True
            continue
        filtered.append(value)
    series = filtered

library_used = "stdlib"
try:
    import numpy as np
except Exception:
    np = None

if series and np is not None:
    arr = np.array(series, dtype=float)
    series_average = float(arr.mean())
    rolling_mean = float(arr[-min(3, len(arr)):].mean())
    rolling_std = float(arr.std()) if len(arr) >= 2 else 0.0
    library_used = "numpy"
elif series:
    series_average = float(statistics.fmean(series))
    rolling_mean = float(statistics.fmean(series[-min(3, len(series)):]))
    rolling_std = float(statistics.pstdev(series)) if len(series) >= 2 else 0.0
else:
    series_average = 0.0
    rolling_mean = 0.0
    rolling_std = 0.0

deltas = [float(series[i] - series[i - 1]) for i in range(1, len(series))] if len(series) >= 2 else []
average_delta = float(statistics.fmean(deltas)) if deltas else 0.0
naive_reference_forecast = float(series[-1] + average_delta) if series else 0.0
residuals = [float(series[i] - (series[i - 1] + average_delta)) for i in range(1, len(series))] if len(series) >= 2 else []
backtest_mae = None
backtest_rmse = None
backtest_mape = None
if len(series) >= 4:
    errors = []
    relative = []
    for end in range(3, len(series)):
        train = series[:end]
        train_deltas = [float(train[i] - train[i - 1]) for i in range(1, len(train))]
        predicted = float(train[-1] + (statistics.fmean(train_deltas) if train_deltas else 0.0))
        actual = float(series[end])
        errors.append(actual - predicted)
        if actual:
            relative.append(abs((actual - predicted) / actual))
    if errors:
        abs_errors = [abs(x) for x in errors]
        squared = [x * x for x in errors]
        backtest_mae = float(statistics.fmean(abs_errors))
        backtest_rmse = float(math.sqrt(statistics.fmean(squared)))
        backtest_mape = float(statistics.fmean(relative)) if relative else 0.0

stability_ratio = float(rolling_std / max(abs(series_average), 1e-6)) if series else 0.0
status = "ok" if len(series) >= 3 else "partial"

history_title = f"{subproblem['title']}: historical series and naive validation reference"
residual_title = f"{subproblem['title']}: one-step residual diagnostics"
history_file = "forecast_history.svg"
residual_file = "forecast_residuals.svg"

def _write_history_chart(path):
    values = list(series) or [0.0]
    chart_values = values + [naive_reference_forecast, rolling_mean]
    width = 760
    height = 420
    left = 70
    right = 50
    top = 50
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    ymin = min(chart_values)
    ymax = max(chart_values)
    if ymin == ymax:
        ymin -= 1.0
        ymax += 1.0
    def _xy(index, value, total):
        x = left + plot_w * index / max(total - 1, 1)
        y = top + plot_h * (1.0 - (float(value) - ymin) / (ymax - ymin))
        return x, y
    points = [_xy(i, values[i], len(values) + 1) for i in range(len(values))]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    rolling_y = _xy(0, rolling_mean, 2)[1]
    ref_point = _xy(len(values), naive_reference_forecast, len(values) + 1)
    labels = "".join(
        f"<text x='{_xy(i, values[i], len(values) + 1)[0]:.1f}' y='380' font-size='12' text-anchor='middle'>t{i + 1}</text>"
        for i in range(len(values))
    )
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{width/2:.1f}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{history_title}</text>
<line x1='{left}' y1='{height-bottom}' x2='{width-right}' y2='{height-bottom}' stroke='#111827' stroke-width='2'/>
<line x1='{left}' y1='{top}' x2='{left}' y2='{height-bottom}' stroke='#111827' stroke-width='2'/>
<line x1='{left}' y1='{rolling_y:.1f}' x2='{width-right}' y2='{rolling_y:.1f}' stroke='#f59e0b' stroke-width='2' stroke-dasharray='6 4'/>
<polyline points='{polyline}' fill='none' stroke='#2563eb' stroke-width='3'/>
<circle cx='{ref_point[0]:.1f}' cy='{ref_point[1]:.1f}' r='5' fill='#dc2626'/>
<text x='{ref_point[0]:.1f}' y='{ref_point[1]-10:.1f}' font-size='12' text-anchor='middle' fill='#dc2626'>ref={naive_reference_forecast:.2f}</text>
{labels}
</svg>"""
    Path(path).write_text(svg, encoding="utf-8")

def _write_residual_chart(path):
    values = list(residuals) or [0.0]
    width = 760
    height = 420
    left = 70
    right = 50
    top = 50
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    ymin = min(values + [0.0])
    ymax = max(values + [0.0])
    if ymin == ymax:
        ymin -= 1.0
        ymax += 1.0
    def _y(value):
        return top + plot_h * (1.0 - (float(value) - ymin) / (ymax - ymin))
    zero_y = _y(0.0)
    bars = []
    labels = []
    for index, value in enumerate(values):
        x = left + plot_w * index / max(len(values), 1)
        target_y = _y(value)
        y = min(zero_y, target_y)
        bar_h = abs(zero_y - target_y)
        fill = "#dc2626" if value >= 0 else "#2563eb"
        bars.append(f"<rect x='{x+8:.1f}' y='{y:.1f}' width='28' height='{max(bar_h, 1.5):.1f}' fill='{fill}' rx='4'/>")
        labels.append(f"<text x='{x+22:.1f}' y='380' font-size='12' text-anchor='middle'>r{index + 1}</text>")
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{width/2:.1f}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{residual_title}</text>
<line x1='{left}' y1='{zero_y:.1f}' x2='{width-right}' y2='{zero_y:.1f}' stroke='#111827' stroke-width='2'/>
{''.join(bars)}
{''.join(labels)}
</svg>"""
    Path(path).write_text(svg, encoding="utf-8")

_write_history_chart(history_file)
_write_residual_chart(residual_file)

result = {
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "forecast_validation_template",
    "objective": analysis.get("objective") or "Validate forecast behavior and produce diagnostic charts for a candidate forecasting algorithm.",
    "assumptions": analysis.get("assumptions") or ["Observed values are treated as a short validation window rather than a final forecasting model."],
    "constraints": analysis.get("constraints") or ["The fallback template does not select the final forecasting algorithm for the LLM."],
    "result_summary": f"Generated a forecast validation bundle for horizon={forecast_horizon} using {len(series)} observed points with {library_used}.",
    "evidence": [
        "template_used=forecast_validation_template",
        f"library_used={library_used}",
        f"table_name={table_name or 'none'}",
        f"selected_column={selected_column or 'none'}",
        f"historical_point_count={len(series)}",
        f"average_delta={average_delta}",
    ],
    "numeric_results": {
        "forecast_horizon": forecast_horizon,
        "historical_point_count": len(series),
        "series_average": round(series_average, 4),
        "rolling_mean": round(rolling_mean, 4),
        "rolling_std": round(rolling_std, 4),
        "average_delta": round(average_delta, 4),
        "naive_reference_forecast": round(naive_reference_forecast, 4),
        "backtest_mae": round(backtest_mae, 4) if backtest_mae is not None else 0.0,
        "backtest_rmse": round(backtest_rmse, 4) if backtest_rmse is not None else 0.0,
        "backtest_mape": round(backtest_mape, 4) if backtest_mape is not None else 0.0,
        "stability_ratio": round(stability_ratio, 4),
    },
    "figure_titles": [history_title, residual_title],
    "artifacts": ["result.json", "forecast_validation.json", history_file, residual_file],
    "verification_checks": [
        f"series_length_check:{'passed' if len(series) >= 3 else 'limited'}",
        f"naive_backtest:{'passed' if backtest_mae is not None else 'insufficient_history'}",
        f"multi_chart_generation:{'passed' if len(series) > 0 else 'limited'}",
    ],
    "constraint_checks": [
        f"horizon_nonnegative:{'passed' if forecast_horizon >= 0 else 'failed'}",
        f"history_available:{'passed' if len(series) >= 2 else 'failed'}",
    ],
    "error_metrics": {
        "backtest_mae": round(backtest_mae, 4) if backtest_mae is not None else 0.0,
        "backtest_rmse": round(backtest_rmse, 4) if backtest_rmse is not None else 0.0,
        "backtest_mape": round(backtest_mape, 4) if backtest_mape is not None else 0.0,
    },
    "robustness_checks": [
        f"stability_ratio={round(stability_ratio, 4)}",
        f"rolling_mean_minus_last={round(rolling_mean - (series[-1] if series else 0.0), 4)}",
    ],
    "suspicious_points": (
        ([f"high_backtest_mape={round(backtest_mape, 4)}"] if backtest_mape is not None and backtest_mape > 0.35 else [])
        + ([f"series_variability_high={round(stability_ratio, 4)}"] if stability_ratio > 0.4 else [])
    ),
    "final_verdict": "validated" if len(series) >= 4 else "needs_review",
    "plot_code_hint": "See forecast_history.svg and forecast_residuals.svg generation in solver_*.py.",
    "next_steps": [
        "Run the LLM-proposed forecasting algorithm and compare it against these diagnostic error metrics.",
        "Use a hold-out window or rolling validation split before trusting the final forecast.",
    ],
}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("forecast_validation.json").write_text(
    json.dumps(
        {
            "series": series,
            "series_average": series_average,
            "average_delta": average_delta,
            "naive_reference_forecast": naive_reference_forecast,
            "residuals": residuals,
            "backtest_mae": backtest_mae,
            "backtest_rmse": backtest_rmse,
            "backtest_mape": backtest_mape,
            "stability_ratio": stability_ratio,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))