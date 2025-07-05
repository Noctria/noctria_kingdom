from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from typing import Optional
from datetime import datetime
import json

from core.path_config import DATA_DIR
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(DATA_DIR.parent / "noctria_gui" / "templates"))
router = APIRouter()

PUSH_LOG_PATH = DATA_DIR / "push_logs" / "push_history.json"

# ✅ Pushログを読み込む
def load_push_logs():
    if PUSH_LOG_PATH.exists():
        with open(PUSH_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ✅ /push-history ページ表示（検索・ソート対応）
@router.get("/push-history", response_class=HTMLResponse)
async def view_push_history(
    request: Request,
    sort: str = "desc",
    q: Optional[str] = None
):
    logs = load_push_logs()

    # 🔍 キーワードフィルタ（戦略名・コミットメッセージ）
    if q:
        q_lower = q.lower()
        logs = [
            log for log in logs
            if q_lower in log.get("strategy", "").lower()
            or q_lower in log.get("commit_message", "").lower()
        ]

    # 📅 ソート（昇順 or 降順）
    def parse_ts(log):
        try:
            return datetime.fromisoformat(log["timestamp"])
        except Exception:
            return datetime.min

    reverse = (sort != "asc")
    logs.sort(key=parse_ts, reverse=reverse)

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "push_logs": logs,
        "query": q or ""
    })
