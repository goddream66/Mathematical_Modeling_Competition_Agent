from __future__ import annotations

import json


def build_forecast_validation_solver_code(context: dict[str, object]) -> tuple[str, str]:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    title = str(context.get("subproblem", {}).get("title") or "subproblem")
    summary = f"Forecast validation template generated a diagnostic bundle for {title}."
    code = f"""from __future__ import annotations
import json
import math
import re
import statistics
from pathlib import Path

context = {context_json}
subproblem = context["subproblem"]
analysis = subproblem["analysis"]
tables = [table for table in context.get("input_data", {{}}).get("tables", []) if table.get("kind") == "table"]
text = subproblem["text"] or context["problem_text"]
numbers = [float(x) for x in re.findall(r"-?\\d+(?:\\.\\d+)?", text)]
horizon_match = re.search(r"(?:next|future|ahead|forecast|预测)\\D*(\\d+)", text, re.IGNORECASE)
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
        lower_map = {{str(col).lower(): str(col) for col in numeric_columns}}
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

history_title = f"{{subproblem['title']}}: historical series and naive validation reference"
residual_title = f"{{subproblem['title']}}: one-step residual diagnostics"
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
    polyline = " ".join(f"{{x:.1f}},{{y:.1f}}" for x, y in points)
    rolling_y = _xy(0, rolling_mean, 2)[1]
    ref_point = _xy(len(values), naive_reference_forecast, len(values) + 1)
    labels = "".join(
        f"<text x='{{_xy(i, values[i], len(values) + 1)[0]:.1f}}' y='380' font-size='12' text-anchor='middle'>t{{i + 1}}</text>"
        for i in range(len(values))
    )
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{history_title}}</text>
<line x1='{{left}}' y1='{{height-bottom}}' x2='{{width-right}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
<line x1='{{left}}' y1='{{top}}' x2='{{left}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
<line x1='{{left}}' y1='{{rolling_y:.1f}}' x2='{{width-right}}' y2='{{rolling_y:.1f}}' stroke='#f59e0b' stroke-width='2' stroke-dasharray='6 4'/>
<polyline points='{{polyline}}' fill='none' stroke='#2563eb' stroke-width='3'/>
<circle cx='{{ref_point[0]:.1f}}' cy='{{ref_point[1]:.1f}}' r='5' fill='#dc2626'/>
<text x='{{ref_point[0]:.1f}}' y='{{ref_point[1]-10:.1f}}' font-size='12' text-anchor='middle' fill='#dc2626'>ref={{naive_reference_forecast:.2f}}</text>
{{labels}}
</svg>\"\"\"
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
        bars.append(f"<rect x='{{x+8:.1f}}' y='{{y:.1f}}' width='28' height='{{max(bar_h, 1.5):.1f}}' fill='{{fill}}' rx='4'/>")
        labels.append(f"<text x='{{x+22:.1f}}' y='380' font-size='12' text-anchor='middle'>r{{index + 1}}</text>")
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{residual_title}}</text>
<line x1='{{left}}' y1='{{zero_y:.1f}}' x2='{{width-right}}' y2='{{zero_y:.1f}}' stroke='#111827' stroke-width='2'/>
{{''.join(bars)}}
{{''.join(labels)}}
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

_write_history_chart(history_file)
_write_residual_chart(residual_file)

result = {{
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "forecast_validation_template",
    "objective": analysis.get("objective") or "Validate forecast behavior and produce diagnostic charts for a candidate forecasting algorithm.",
    "assumptions": analysis.get("assumptions") or ["Observed values are treated as a short validation window rather than a final forecasting model."],
    "constraints": analysis.get("constraints") or ["The fallback template does not select the final forecasting algorithm for the LLM."],
    "result_summary": f"Generated a forecast validation bundle for horizon={{forecast_horizon}} using {{len(series)}} observed points with {{library_used}}.",
    "evidence": [
        "template_used=forecast_validation_template",
        f"library_used={{library_used}}",
        f"table_name={{table_name or 'none'}}",
        f"selected_column={{selected_column or 'none'}}",
        f"historical_point_count={{len(series)}}",
        f"average_delta={{average_delta}}",
    ],
    "numeric_results": {{
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
    }},
    "figure_titles": [history_title, residual_title],
    "artifacts": ["result.json", "forecast_validation.json", history_file, residual_file],
    "verification_checks": [
        f"series_length_check:{{'passed' if len(series) >= 3 else 'limited'}}",
        f"naive_backtest:{{'passed' if backtest_mae is not None else 'insufficient_history'}}",
        f"multi_chart_generation:{{'passed' if len(series) > 0 else 'limited'}}",
    ],
    "constraint_checks": [
        f"horizon_nonnegative:{{'passed' if forecast_horizon >= 0 else 'failed'}}",
        f"history_available:{{'passed' if len(series) >= 2 else 'failed'}}",
    ],
    "error_metrics": {{
        "backtest_mae": round(backtest_mae, 4) if backtest_mae is not None else 0.0,
        "backtest_rmse": round(backtest_rmse, 4) if backtest_rmse is not None else 0.0,
        "backtest_mape": round(backtest_mape, 4) if backtest_mape is not None else 0.0,
    }},
    "robustness_checks": [
        f"stability_ratio={{round(stability_ratio, 4)}}",
        f"rolling_mean_minus_last={{round(rolling_mean - (series[-1] if series else 0.0), 4)}}",
    ],
    "suspicious_points": (
        ([f"high_backtest_mape={{round(backtest_mape, 4)}}"] if backtest_mape is not None and backtest_mape > 0.35 else [])
        + ([f"series_variability_high={{round(stability_ratio, 4)}}"] if stability_ratio > 0.4 else [])
    ),
    "final_verdict": "validated" if len(series) >= 4 else "needs_review",
    "plot_code_hint": "See forecast_history.svg and forecast_residuals.svg generation in solver_*.py.",
    "next_steps": [
        "Run the LLM-proposed forecasting algorithm and compare it against these diagnostic error metrics.",
        "Use a hold-out window or rolling validation split before trusting the final forecast.",
    ],
}}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("forecast_validation.json").write_text(
    json.dumps(
        {{
            "series": series,
            "series_average": series_average,
            "average_delta": average_delta,
            "naive_reference_forecast": naive_reference_forecast,
            "residuals": residuals,
            "backtest_mae": backtest_mae,
            "backtest_rmse": backtest_rmse,
            "backtest_mape": backtest_mape,
            "stability_ratio": stability_ratio,
        }},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))
"""
    return summary, code


def build_optimization_validation_solver_code(context: dict[str, object]) -> tuple[str, str]:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    title = str(context.get("subproblem", {}).get("title") or "subproblem")
    summary = f"Optimization validation template generated a diagnostic bundle for {title}."
    code = f"""from __future__ import annotations
import json
import re
from pathlib import Path

context = {context_json}
subproblem = context["subproblem"]
analysis = subproblem["analysis"]
tables = [table for table in context.get("input_data", {{}}).get("tables", []) if table.get("kind") == "table"]
text = subproblem["text"] or context["problem_text"]
numbers = [float(x) for x in re.findall(r"-?\\d+(?:\\.\\d+)?", text)]
budget = max(numbers) if numbers else 0.0

def _pick_column(table, keywords):
    for column in table.get("columns", []):
        lower = str(column).lower()
        if any(keyword in lower for keyword in keywords):
            return column
    return None

candidate_costs = [float(x) for x in numbers if x > 0]
candidate_values = list(candidate_costs)
table_name = None
cost_column = None
value_column = None
for table in tables:
    cost_column = _pick_column(table, ["cost", "price", "expense", "weight", "budget"])
    value_column = _pick_column(table, ["value", "profit", "revenue", "score", "benefit"])
    if cost_column:
        raw_costs = [
            float(row[cost_column])
            for row in table.get("rows", [])
            if isinstance(row.get(cost_column), (int, float)) and not isinstance(row.get(cost_column), bool)
        ]
        if raw_costs:
            candidate_costs = raw_costs
            if value_column:
                candidate_values = [
                    float(row[value_column])
                    for row in table.get("rows", [])
                    if isinstance(row.get(value_column), (int, float)) and not isinstance(row.get(value_column), bool)
                ]
                if len(candidate_values) != len(candidate_costs):
                    candidate_values = list(candidate_costs)
            table_name = table.get("name", "table")
            break

if budget in candidate_costs and len(candidate_costs) > 1:
    candidate_costs.remove(budget)
if len(candidate_values) != len(candidate_costs):
    candidate_values = list(candidate_costs)
feasible_costs = [float(x) for x in candidate_costs if budget and x <= budget]
infeasible_costs = [float(x) for x in candidate_costs if budget and x > budget]
value_per_cost = [
    float(candidate_values[i] / max(candidate_costs[i], 1e-6))
    for i in range(min(len(candidate_costs), len(candidate_values)))
]
mean_cost = float(sum(candidate_costs) / len(candidate_costs)) if candidate_costs else 0.0
max_cost = float(max(candidate_costs)) if candidate_costs else 0.0
mean_value = float(sum(candidate_values) / len(candidate_values)) if candidate_values else 0.0
mean_value_per_cost = float(sum(value_per_cost) / len(value_per_cost)) if value_per_cost else 0.0
budget_feasibility_ratio = float(len(feasible_costs) / len(candidate_costs)) if candidate_costs else 0.0
min_budget_slack = float(min((budget - value) for value in feasible_costs)) if feasible_costs else 0.0
status = "ok" if candidate_costs and budget else "partial"

cost_title = f"{{subproblem['title']}}: candidate cost profile vs budget"
ratio_title = f"{{subproblem['title']}}: value-cost validation profile"
cost_file = "optimization_cost_profile.svg"
ratio_file = "optimization_value_cost.svg"

def _write_cost_chart(path):
    values = list(candidate_costs[:8]) or [0.0]
    width = 720
    height = 420
    left = 70
    top = 60
    bottom = 60
    chart_h = height - top - bottom
    max_value = max(values + [budget, 1.0])
    step = 70
    bars = []
    labels = []
    for index, value in enumerate(values):
        x = left + index * step
        bar_h = chart_h * float(value) / max_value
        y = top + chart_h - bar_h
        fill = "#2563eb" if value <= budget else "#dc2626"
        bars.append(f"<rect x='{{x}}' y='{{y:.1f}}' width='32' height='{{bar_h:.1f}}' fill='{{fill}}' rx='4'/>")
        labels.append(f"<text x='{{x + 16}}' y='380' font-size='12' text-anchor='middle'>c{{index + 1}}</text>")
    budget_y = top + chart_h - chart_h * float(budget) / max_value if max_value else top + chart_h
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{cost_title}}</text>
<line x1='{{left-10}}' y1='{{height-bottom}}' x2='{{width-30}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
<line x1='{{left-10}}' y1='{{budget_y:.1f}}' x2='{{width-30}}' y2='{{budget_y:.1f}}' stroke='#f59e0b' stroke-width='2' stroke-dasharray='6 4'/>
{{''.join(bars)}}
{{''.join(labels)}}
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

def _write_ratio_chart(path):
    values = list(value_per_cost[:8]) or [0.0]
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
        bars.append(f"<rect x='{{x}}' y='{{y:.1f}}' width='32' height='{{bar_h:.1f}}' fill='#0f766e' rx='4'/>")
        labels.append(f"<text x='{{x + 16}}' y='380' font-size='12' text-anchor='middle'>r{{index + 1}}</text>")
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{ratio_title}}</text>
<line x1='{{left-10}}' y1='{{height-bottom}}' x2='{{width-30}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
{{''.join(bars)}}
{{''.join(labels)}}
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

_write_cost_chart(cost_file)
_write_ratio_chart(ratio_file)

result = {{
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "optimization_validation_template",
    "objective": analysis.get("objective") or "Validate budget, cost, and feasibility structure for a candidate optimization model.",
    "assumptions": analysis.get("assumptions") or ["Detected numbers are treated as candidate costs or values for validation only."],
    "constraints": analysis.get("constraints") or ["The fallback template does not choose a final allocation plan for the LLM."],
    "result_summary": "Generated an optimization validation bundle without selecting a final plan.",
    "evidence": [
        "template_used=optimization_validation_template",
        f"table_name={{table_name or 'none'}}",
        f"cost_column={{cost_column or 'none'}}",
        f"value_column={{value_column or 'none'}}",
        f"budget={{budget}}",
        f"candidate_cost_count={{len(candidate_costs)}}",
    ],
    "numeric_results": {{
        "budget": round(budget, 4),
        "candidate_cost_count": len(candidate_costs),
        "feasible_candidate_count": len(feasible_costs),
        "infeasible_candidate_count": len(infeasible_costs),
        "mean_cost": round(mean_cost, 4),
        "max_cost": round(max_cost, 4),
        "mean_value": round(mean_value, 4),
        "mean_value_per_cost": round(mean_value_per_cost, 4),
        "budget_feasibility_ratio": round(budget_feasibility_ratio, 4),
        "min_budget_slack": round(min_budget_slack, 4),
    }},
    "figure_titles": [cost_title, ratio_title],
    "artifacts": ["result.json", "optimization_validation.json", cost_file, ratio_file],
    "verification_checks": [
        f"budget_detected:{{'passed' if budget > 0 else 'failed'}}",
        f"candidate_costs_detected:{{'passed' if len(candidate_costs) > 0 else 'failed'}}",
        f"multi_chart_generation:{{'passed' if len(candidate_costs) > 0 else 'limited'}}",
    ],
    "constraint_checks": [
        f"single_item_budget_feasibility:{{'passed' if feasible_costs else 'failed'}}",
        f"explicit_budget_constraint:{{'passed' if budget > 0 else 'missing'}}",
    ],
    "error_metrics": {{
        "budget_slack_floor": round(min_budget_slack, 4),
    }},
    "robustness_checks": [
        f"budget_feasibility_ratio={{round(budget_feasibility_ratio, 4)}}",
        f"mean_value_per_cost={{round(mean_value_per_cost, 4)}}",
    ],
    "suspicious_points": (
        (["all_candidates_violate_budget"] if budget_feasibility_ratio == 0.0 and candidate_costs else [])
        + (["value_cost_signal_weak"] if mean_value_per_cost == 0.0 and candidate_values else [])
    ),
    "final_verdict": "validated" if budget > 0 and candidate_costs else "needs_review",
    "plot_code_hint": "See optimization_cost_profile.svg and optimization_value_cost.svg generation in solver_*.py.",
    "next_steps": [
        "Run the LLM-proposed optimization algorithm and compare its allocation against these feasibility diagnostics.",
        "Translate the chosen method into explicit variables and constraints before trusting a final decision plan.",
    ],
}}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("optimization_validation.json").write_text(
    json.dumps(
        {{
            "candidate_costs": candidate_costs[:20],
            "candidate_values": candidate_values[:20],
            "feasible_costs": feasible_costs[:20],
            "budget": budget,
            "budget_feasibility_ratio": budget_feasibility_ratio,
            "mean_value_per_cost": mean_value_per_cost,
            "min_budget_slack": min_budget_slack,
        }},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))
"""
    return summary, code


def build_path_validation_solver_code(context: dict[str, object]) -> tuple[str, str]:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    title = str(context.get("subproblem", {}).get("title") or "subproblem")
    summary = f"Path validation template generated a diagnostic bundle for {title}."
    code = f"""from __future__ import annotations
import json
import re
from pathlib import Path

context = {context_json}
subproblem = context["subproblem"]
analysis = subproblem["analysis"]
tables = [table for table in context.get("input_data", {{}}).get("tables", []) if table.get("kind") == "table"]
text = subproblem["text"] or context["problem_text"]
numbers = [float(x) for x in re.findall(r"-?\\d+(?:\\.\\d+)?", text)]
table_name = None
source_column = None
target_column = None
weight_column = None
node_set = set()
edge_rows = []

for table in tables:
    lower_map = {{str(column).lower(): str(column) for column in table.get("columns", [])}}
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

weight_title = f"{{subproblem['title']}}: edge weight diagnostics"
cumulative_title = f"{{subproblem['title']}}: cumulative distance diagnostics"
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
        bars.append(f"<rect x='{{x}}' y='{{y:.1f}}' width='32' height='{{bar_h:.1f}}' fill='#0f766e' rx='4'/>")
        labels.append(f"<text x='{{x + 16}}' y='380' font-size='12' text-anchor='middle'>e{{index + 1}}</text>")
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{weight_title}}</text>
<line x1='{{left-10}}' y1='{{height-bottom}}' x2='{{width-30}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
{{''.join(bars)}}
{{''.join(labels)}}
</svg>\"\"\"
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
    polyline = " ".join(f"{{x:.1f}},{{y:.1f}}" for x, y in points) if points else ""
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{cumulative_title}}</text>
<line x1='{{left}}' y1='{{height-bottom}}' x2='{{width-right}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
<polyline points='{{polyline}}' fill='none' stroke='#2563eb' stroke-width='3'/>
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

_write_bar_chart(weight_file)
_write_line_chart(cumulative_file)

result = {{
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "path_validation_template",
    "objective": analysis.get("objective") or "Validate network weight structure and generate path diagnostics without selecting a final route.",
    "assumptions": analysis.get("assumptions") or ["Detected numbers are treated as edge-weight evidence only."],
    "constraints": analysis.get("constraints") or ["The fallback template does not choose a final route or path algorithm for the LLM."],
    "result_summary": "Generated a path/network validation bundle without selecting a final route.",
    "evidence": [
        "template_used=path_validation_template",
        f"table_name={{table_name or 'none'}}",
        f"source_column={{source_column or 'none'}}",
        f"target_column={{target_column or 'none'}}",
        f"weight_column={{weight_column or 'none'}}",
        f"edge_count_estimate={{edge_count}}",
    ],
    "numeric_results": {{
        "edge_count_estimate": edge_count,
        "graph_node_count": graph_node_count,
        "path_weight_mean": round(average_edge_weight, 4),
        "max_edge_weight": round(max_edge_weight, 4),
        "min_edge_weight": round(min_edge_weight, 4),
        "distance_reference_sum": round(distance_reference_sum, 4),
        "path_density_ratio": round(float(edge_count / max(graph_node_count, 1)), 4) if edge_count else 0.0,
    }},
    "figure_titles": [weight_title, cumulative_title],
    "artifacts": ["result.json", "path_validation.json", weight_file, cumulative_file],
    "verification_checks": [
        f"weight_detection:{{'passed' if weights else 'failed'}}",
        f"explicit_graph_edges:{{'passed' if edge_rows else 'missing'}}",
        f"multi_chart_generation:{{'passed' if weights else 'limited'}}",
    ],
    "constraint_checks": [
        f"positive_weight_check:{{'passed' if all(value >= 0 for value in weights) else 'failed'}}",
        f"graph_context_available:{{'passed' if edge_rows else 'limited'}}",
    ],
    "error_metrics": {{
        "weight_range": round(max_edge_weight - min_edge_weight, 4) if weights else 0.0,
    }},
    "robustness_checks": [
        f"average_edge_weight={{round(average_edge_weight, 4)}}",
        f"cumulative_distance_last={{round(cumulative_weights[-1], 4) if cumulative_weights else 0.0}}",
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
}}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("path_validation.json").write_text(
    json.dumps(
        {{
            "weights": weights[:20],
            "edge_count_estimate": edge_count,
            "graph_node_count": graph_node_count,
            "distance_reference_sum": distance_reference_sum,
            "cumulative_weights": cumulative_weights,
        }},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))
"""
    return summary, code


def build_evaluation_validation_solver_code(context: dict[str, object]) -> tuple[str, str]:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    title = str(context.get("subproblem", {}).get("title") or "subproblem")
    summary = f"Evaluation validation template generated a diagnostic bundle for {title}."
    code = f"""from __future__ import annotations
import json
import math
import re
import statistics
from pathlib import Path

context = {context_json}
subproblem = context["subproblem"]
analysis = subproblem["analysis"]
tables = [table for table in context.get("input_data", {{}}).get("tables", []) if table.get("kind") == "table"]
text = subproblem["text"] or context["problem_text"]
numbers = [float(x) for x in re.findall(r"-?\\d+(?:\\.\\d+)?", text)]
indicator_count = len(analysis.get("key_variables") or [])
table_name = None
score_columns = []

for table in tables:
    numeric_columns = []
    for column in table.get("columns", []):
        if any(isinstance(row.get(column), (int, float)) and not isinstance(row.get(column), bool) for row in table.get("rows", [])):
            numeric_columns.append(column)
    if numeric_columns:
        table_name = table.get("name", "table")
        score_columns = list(numeric_columns)
        values = []
        for row in table.get("rows", []):
            row_values = [float(row[column]) for column in score_columns if isinstance(row.get(column), (int, float)) and not isinstance(row.get(column), bool)]
            if row_values:
                values.append(float(sum(row_values) / len(row_values)))
        if values:
            numbers = values
            indicator_count = len(score_columns)
            break

average_score = float(statistics.fmean(numbers)) if numbers else 0.0
max_score = float(max(numbers)) if numbers else 0.0
score_std = float(statistics.pstdev(numbers)) if len(numbers) >= 2 else 0.0
total_score = float(sum(numbers))
normalized_scores = [float(x / total_score) if total_score else 0.0 for x in numbers]
entropy = 0.0
for value in normalized_scores:
    if value > 0:
        entropy -= float(value * math.log(value))
status = "ok" if numbers else "partial"

score_title = f"{{subproblem['title']}}: score distribution diagnostics"
normalized_title = f"{{subproblem['title']}}: normalized indicator profile"
score_file = "evaluation_scores.svg"
normalized_file = "evaluation_normalized.svg"

def _write_score_chart(path):
    values = list(numbers[:8]) or [0.0]
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
        bars.append(f"<rect x='{{x}}' y='{{y:.1f}}' width='32' height='{{bar_h:.1f}}' fill='#7c3aed' rx='4'/>")
        labels.append(f"<text x='{{x + 16}}' y='380' font-size='12' text-anchor='middle'>s{{index + 1}}</text>")
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{score_title}}</text>
<line x1='{{left-10}}' y1='{{height-bottom}}' x2='{{width-30}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
{{''.join(bars)}}
{{''.join(labels)}}
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

def _write_normalized_chart(path):
    values = list(normalized_scores[:8]) or [0.0]
    width = 720
    height = 420
    left = 70
    right = 50
    top = 60
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    ymin = 0.0
    ymax = max(values + [1.0])
    def _xy(index, value, total):
        x = left + plot_w * index / max(total - 1, 1)
        y = top + plot_h * (1.0 - (float(value) - ymin) / max(ymax - ymin, 1e-6))
        return x, y
    points = [_xy(i, values[i], len(values)) for i in range(len(values))]
    polyline = " ".join(f"{{x:.1f}},{{y:.1f}}" for x, y in points) if points else ""
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{normalized_title}}</text>
<line x1='{{left}}' y1='{{height-bottom}}' x2='{{width-right}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
<polyline points='{{polyline}}' fill='none' stroke='#2563eb' stroke-width='3'/>
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

_write_score_chart(score_file)
_write_normalized_chart(normalized_file)

result = {{
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "evaluation_validation_template",
    "objective": analysis.get("objective") or "Validate score structure and produce diagnostic charts for a candidate evaluation model.",
    "assumptions": analysis.get("assumptions") or ["Detected numbers are treated as score evidence only."],
    "constraints": analysis.get("constraints") or ["The fallback template does not choose a final ranking for the LLM."],
    "result_summary": "Generated an evaluation validation bundle without producing a final ranking.",
    "evidence": [
        "template_used=evaluation_validation_template",
        f"table_name={{table_name or 'none'}}",
        f"score_column_count={{len(score_columns)}}",
        f"indicator_count={{indicator_count}}",
        f"number_count={{len(numbers)}}",
    ],
    "numeric_results": {{
        "indicator_count": indicator_count,
        "number_count": len(numbers),
        "average_score": round(average_score, 4),
        "max_score": round(max_score, 4),
        "score_std": round(score_std, 4),
        "normalized_entropy": round(entropy, 4),
        "weight_balance_score": round(max(normalized_scores) - min(normalized_scores), 4) if normalized_scores else 0.0,
    }},
    "figure_titles": [score_title, normalized_title],
    "artifacts": ["result.json", "evaluation_validation.json", score_file, normalized_file],
    "verification_checks": [
        f"score_detection:{{'passed' if numbers else 'failed'}}",
        f"indicator_context:{{'passed' if indicator_count > 0 else 'limited'}}",
        f"multi_chart_generation:{{'passed' if numbers else 'limited'}}",
    ],
    "constraint_checks": [
        f"nonnegative_score_check:{{'passed' if all(value >= 0 for value in numbers) else 'failed'}}",
        f"normalization_ready:{{'passed' if total_score > 0 else 'failed'}}",
    ],
    "error_metrics": {{
        "score_std": round(score_std, 4),
    }},
    "robustness_checks": [
        f"normalized_entropy={{round(entropy, 4)}}",
        f"weight_balance_score={{round(max(normalized_scores) - min(normalized_scores), 4) if normalized_scores else 0.0}}",
    ],
    "suspicious_points": (
        (["score_variance_low"] if score_std < 1e-6 and len(numbers) >= 2 else [])
        + (["normalization_unstable"] if total_score <= 0 else [])
    ),
    "final_verdict": "validated" if numbers else "needs_review",
    "plot_code_hint": "See evaluation_scores.svg and evaluation_normalized.svg generation in solver_*.py.",
    "next_steps": [
        "Run the LLM-proposed evaluation method and compare its ranking logic against these score diagnostics.",
        "Define indicator directions and weighting rules before trusting a final ranking.",
    ],
}}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("evaluation_validation.json").write_text(
    json.dumps(
        {{
            "scores": numbers[:20],
            "normalized_scores": normalized_scores[:20],
            "average_score": average_score,
            "score_std": score_std,
            "normalized_entropy": entropy,
        }},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))
"""
    return summary, code


def build_generic_validation_solver_code(context: dict[str, object]) -> tuple[str, str]:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    title = str(context.get("subproblem", {}).get("title") or "subproblem")
    summary = f"Generic validation template generated a diagnostic bundle for {title}."
    code = f"""from __future__ import annotations
import json
import re
from pathlib import Path

context = {context_json}
subproblem = context["subproblem"]
analysis = subproblem["analysis"]
text = subproblem["text"] or context["problem_text"]
numbers = [float(x) for x in re.findall(r"-?\\d+(?:\\.\\d+)?", text)]
mean_value = float(sum(numbers) / len(numbers)) if numbers else 0.0
max_value = float(max(numbers)) if numbers else 0.0
min_value = float(min(numbers)) if numbers else 0.0
cumulative = []
running = 0.0
for value in numbers[:12]:
    running += float(value)
    cumulative.append(round(running, 4))
status = "ok" if numbers else "partial"

overview_title = f"{{subproblem['title']}}: extracted numeric overview"
cumulative_title = f"{{subproblem['title']}}: cumulative numeric signal"
overview_file = "generic_overview.svg"
cumulative_file = "generic_cumulative.svg"

def _write_bar_chart(path):
    values = list(numbers[:8]) or [0.0]
    width = 720
    height = 420
    left = 70
    top = 60
    bottom = 60
    chart_h = height - top - bottom
    max_value = max([abs(float(v)) for v in values] + [1.0])
    step = 70
    bars = []
    labels = []
    for index, value in enumerate(values):
        x = left + index * step
        bar_h = chart_h * abs(float(value)) / max_value
        y = top + chart_h - bar_h
        bars.append(f"<rect x='{{x}}' y='{{y:.1f}}' width='32' height='{{bar_h:.1f}}' fill='#2563eb' rx='4'/>")
        labels.append(f"<text x='{{x + 16}}' y='380' font-size='12' text-anchor='middle'>n{{index + 1}}</text>")
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{overview_title}}</text>
<line x1='{{left-10}}' y1='{{height-bottom}}' x2='{{width-30}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
{{''.join(bars)}}
{{''.join(labels)}}
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

def _write_line_chart(path):
    values = list(cumulative) or [0.0]
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
    polyline = " ".join(f"{{x:.1f}},{{y:.1f}}" for x, y in points) if points else ""
    svg = f\"\"\"<svg xmlns='http://www.w3.org/2000/svg' width='{{width}}' height='{{height}}' viewBox='0 0 {{width}} {{height}}'>
<rect width='100%' height='100%' fill='white'/>
<text x='{{width/2:.1f}}' y='28' font-size='22' text-anchor='middle' fill='#111827'>{{cumulative_title}}</text>
<line x1='{{left}}' y1='{{height-bottom}}' x2='{{width-right}}' y2='{{height-bottom}}' stroke='#111827' stroke-width='2'/>
<polyline points='{{polyline}}' fill='none' stroke='#0f766e' stroke-width='3'/>
</svg>\"\"\"
    Path(path).write_text(svg, encoding="utf-8")

_write_bar_chart(overview_file)
_write_line_chart(cumulative_file)

result = {{
    "subproblem_title": subproblem["title"],
    "status": status,
    "method": analysis.get("chosen_method") or "generic_validation_template",
    "objective": analysis.get("objective") or "Validate available numeric evidence before a domain-specific solver is chosen.",
    "assumptions": analysis.get("assumptions") or ["Use the current problem statement as the primary evidence source."],
    "constraints": analysis.get("constraints") or ["Formal constraints still need to be written explicitly."],
    "result_summary": ("Generated a generic validation bundle from extracted numeric evidence." if numbers else "No direct numeric signal was found; additional data is required."),
    "evidence": [
        "template_used=generic_validation_template",
        f"number_count={{len(numbers)}}",
        f"chosen_method={{analysis.get('chosen_method') or 'generic_validation_template'}}",
    ],
    "numeric_results": {{
        "detected_number_count": len(numbers),
        "mean_value": round(mean_value, 4) if numbers else 0.0,
        "max_value": round(max_value, 4) if numbers else 0.0,
        "min_value": round(min_value, 4) if numbers else 0.0,
    }},
    "figure_titles": [overview_title, cumulative_title] if numbers else [],
    "artifacts": ["result.json", "generic_validation.json", overview_file, cumulative_file] if numbers else ["result.json", "generic_validation.json"],
    "verification_checks": [
        f"numeric_signal_detected:{{'passed' if numbers else 'failed'}}",
        f"multi_chart_generation:{{'passed' if numbers else 'limited'}}",
    ],
    "constraint_checks": ["constraint_review:manual_follow_up_required"],
    "error_metrics": {{}},
    "robustness_checks": [f"cumulative_last={{cumulative[-1] if cumulative else 0.0}}"],
    "suspicious_points": (["insufficient_numeric_signal"] if not numbers else []),
    "final_verdict": "needs_review",
    "plot_code_hint": "See generic_overview.svg and generic_cumulative.svg generation in solver_*.py." if numbers else "",
    "next_steps": [
        "Pass the LLM-proposed algorithm or structured data into the coding stage for domain-specific validation.",
        "Provide tables, parameters, or constraints before expecting a reliable final answer.",
    ],
}}
Path("result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
Path("generic_validation.json").write_text(
    json.dumps(
        {{
            "numbers": numbers[:20],
            "mean_value": mean_value,
            "max_value": max_value,
            "min_value": min_value,
            "cumulative": cumulative,
        }},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False))
"""
    return summary, code
