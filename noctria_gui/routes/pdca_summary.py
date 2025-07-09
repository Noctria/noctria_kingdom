# routes/pdca_summary.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR

from pathlib import Path
import json

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/pdca/summary", response_class=HTMLResponse)
async def show_pdca_summary(request: Request):
    """
    📊 PDCA再評価結果の集計ダッシュボード
    """
    eval_log_path = LOGS_DIR / "veritas_eval_result.json"
    stats = {
        "count": 0,
        "adopted_count": 0,
        "rejected_count": 0,
        "error_count": 0,
        "avg_win_rate_diff": 0.0,
        "avg_dd_diff": 0.0,
        "improved_win_rate_count": 0,
        "improved_dd_count": 0,
        "win_rate_diffs": [],
        "dd_diffs": [],
    }

    if not eval_log_path.exists():
        return templates.TemplateResponse("pdca_summary.html", {
            "request": request,
            "stats": stats,
        })

    with open(eval_log_path, "r", encoding="utf-8") as f:
        try:
            logs = json.load(f)
        except Exception as e:
            print(f"⚠️ ログ読み込みエラー: {e}")
            logs = []

    total_win_rate_diff = 0.0
    total_dd_diff = 0.0
    valid_count = 0

    for entry in logs:
        status = entry.get("status")
        if status == "adopted":
            stats["adopted_count"] += 1
        elif status == "rejected":
            stats["rejected_count"] += 1
        elif status == "error":
            stats["error_count"] += 1

        # 差分算出
        win_before = entry.get("win_rate_before")
        win_after = entry.get("win_rate_after")
        dd_before = entry.get("max_dd_before")
        dd_after = entry.get("max_dd_after")

        if win_before is not None and win_after is not None:
            diff = win_after - win_before
            stats["win_rate_diffs"].append(diff)
            total_win_rate_diff += diff
            if diff > 0:
                stats["improved_win_rate_count"] += 1
            valid_count += 1

        if dd_before is not None and dd_after is not None:
            dd_diff = dd_before - dd_after  # DDは小さい方が良い
            stats["dd_diffs"].append(dd_diff)
            total_dd_diff += dd_diff
            if dd_diff > 0:
                stats["improved_dd_count"] += 1

    stats["count"] = len(logs)
    if valid_count > 0:
        stats["avg_win_rate_diff"] = round(total_win_rate_diff / valid_count * 100, 2)  # パーセント表記
        stats["avg_dd_diff"] = round(total_dd_diff / valid_count, 2)

    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "stats": stats,
    })
