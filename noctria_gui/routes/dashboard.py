# routes/dashboard.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR, PUSH_LOG_DIR

from collections import defaultdict
from datetime import datetime
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def load_logs_by_date(log_dir):
    """
    ログフォルダ内のJSONファイルを読み込み、日付ごとにカウントを集計
    """
    counter = defaultdict(int)
    for file in os.listdir(log_dir):
        if file.endswith(".json"):
            with open(os.path.join(log_dir, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                date_str = data.get("date")
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        key = date_obj.strftime("%Y-%m-%d")
                        counter[key] += 1
                    except Exception:
                        continue
    return counter


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    📊 中央統治ダッシュボード
    - 昇格数・Push数の件数および日次集計グラフ
    """
    act_counter = load_logs_by_date(str(ACT_LOG_DIR))
    push_counter = load_logs_by_date(str(PUSH_LOG_DIR))

    # 日付で統一ソート
    all_dates = sorted(set(act_counter.keys()) | set(push_counter.keys()))
    promoted_values = [act_counter.get(d, 0) for d in all_dates]
    pushed_values = [push_counter.get(d, 0) for d in all_dates]

    stats = {
        "promoted_count": sum(promoted_values),
        "push_count": sum(pushed_values),
        "dates": all_dates,
        "promoted_values": promoted_values,
        "pushed_values": pushed_values,
    }

    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})
