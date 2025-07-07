from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from collections import defaultdict
from statistics import mean, median
from datetime import datetime
from pathlib import Path
import os
import json
import csv
import io
from typing import Optional, List, Dict, Any

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """文字列を日付(datetime)に変換。失敗時はNone。"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def load_strategy_logs() -> List[Dict[str, Any]]:
    """ACT_LOG_DIR配下の全JSONをロード。辞書型のみ抽出。"""
    data: List[Dict[str, Any]] = []
    log_dir = Path(ACT_LOG_DIR)
    for file in os.listdir(log_dir):
        if file.endswith(".json"):
            path = log_dir / file
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    if isinstance(obj, dict):
                        data.append(obj)
            except Exception:
                continue
    return data


def filter_by_date(
    records: List[Dict[str, Any]],
    from_date: Optional[datetime],
    to_date: Optional[datetime]
) -> List[Dict[str, Any]]:
    """timestampフィールドの日付で範囲フィルタ"""
    filtered = []
    for d in records:
        ts_str = d.get("timestamp", "")[:10]
        ts = parse_date(ts_str)
        if from_date and ts and ts < from_date:
            continue
        if to_date and ts and ts > to_date:
            continue
        filtered.append(d)
    return filtered


def compute_statistics_grouped(
    data: List[Dict[str, Any]],
    mode: str
) -> Dict[str, Dict[str, List[float]]]:
    """
    mode="strategy"なら戦略ごと、mode="tag"ならタグごとに
    各指標ごとのスコア配列を構築。
    """
    stat_map: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for entry in data:
        keys = [entry.get("strategy_name")] if mode == "strategy" else entry.get("tags", [])
        if not keys:
            continue
        for key in keys:
            if not key:
                continue
            for k, v in entry.get("scores", {}).items():
                if isinstance(v, (int, float)):
                    stat_map[key][k].append(v)
    return stat_map


@router.get("/statistics/compare", response_class=HTMLResponse)
async def compare(request: Request) -> HTMLResponse:
    mode = request.query_params.get("mode", "strategy")
    from_date = parse_date(request.query_params.get("from"))
    to_date = parse_date(request.query_params.get("to"))

    all_data = load_strategy_logs()
    filtered = filter_by_date(all_data, from_date, to_date)
    stat_map = compute_statistics_grouped(filtered, mode)

    results = []
    for key, scores in stat_map.items():
        row = {"name": key}
        for metric, values in scores.items():
            if values:
                row[f"{metric}_mean"] = round(mean(values), 3)
                row[f"{metric}_median"] = round(median(values), 3)
            else:
                row[f"{metric}_mean"] = ""
                row[f"{metric}_median"] = ""
        results.append(row)

    return templates.TemplateResponse("statistics_compare.html", {
        "request": request,
        "mode": mode,
        "data": results,
        "filter": {
            "from": request.query_params.get("from", ""),
            "to": request.query_params.get("to", ""),
        },
    })


@router.get("/statistics/compare/export")
async def export_csv(request: Request) -> StreamingResponse:
    mode = request.query_params.get("mode", "strategy")
    from_date = parse_date(request.query_params.get("from"))
    to_date = parse_date(request.query_params.get("to"))

    all_data = load_strategy_logs()
    filtered = filter_by_date(all_data, from_date, to_date)
    stat_map = compute_statistics_grouped(filtered, mode)

    rows = []
    headers = ["name"]
    metric_names = set()

    for key, scores in stat_map.items():
        row = {"name": key}
        for metric, values in scores.items():
            m = round(mean(values), 3) if values else ""
            med = round(median(values), 3) if values else ""
            row[f"{metric}_mean"] = m
            row[f"{metric}_median"] = med
            metric_names.update([f"{metric}_mean", f"{metric}_median"])
        rows.append(row)

    headers.extend(sorted(metric_names))

    # 📊 統計サマリ行追加
    summary_mean = {"name": "📊 平均"}
    summary_median = {"name": "📊 中央値"}
    for metric in metric_names:
        values = [row.get(metric) for row in rows if isinstance(row.get(metric), (int, float))]
        summary_mean[metric] = round(mean(values), 3) if values else ""
        summary_median[metric] = round(median(values), 3) if values else ""

    rows.extend([summary_mean, summary_median])

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=compare_result.csv"
    })
