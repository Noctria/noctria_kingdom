#!/usr/bin/env python3
# coding: utf-8

"""
👑 /king - 中央統治AI NoctriaのAPIルート群
- 評議会の開催（/king/hold-council）
- 評議会ログの保存・取得（/king/history）
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from core.king_noctria import KingNoctria

from datetime import datetime
from pathlib import Path
import json

# ──────────────────────────────
# 📁 ルーターとテンプレート初期化
# ──────────────────────────────
router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 📌 評議会ログファイルの保存先
KING_LOG_PATH = LOGS_DIR / "king_log.json"

# ──────────────────────────────
# 🧩 ユーティリティ関数
# ──────────────────────────────

def load_logs() -> list:
    """📖 評議会ログを読み込む"""
    if KING_LOG_PATH.exists():
        with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_log(entry: dict):
    """📚 評議会ログを追記保存"""
    logs = load_logs()
    logs.append(entry)
    with open(KING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ──────────────────────────────
# 👑 評議会APIエンドポイント
# ──────────────────────────────

@router.post("/king/hold-council")
async def hold_council_api(request: Request):
    """
    🧠 KingNoctriaによる評議会の開催（外部データを元に意思決定）
    - POSTされたmarket_dataを元にhold_council()を実行
    - 結果をJSONで返却し、ログにも保存
    """
    try:
        data = await request.json()
        king = KingNoctria()
        result = king.hold_council(data)

        # ⏺️ 評議会ログの保存
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "market_data": data,
            "result": result
        }
        save_log(log_entry)

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(content={"error": f"Council failed: {str(e)}"}, status_code=500)

# ──────────────────────────────
# 📜 評議会履歴表示ページ
# ──────────────────────────────

@router.get("/king/history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    """
    📜 KingNoctriaによる過去の評議会履歴をGUIで表示
    """
    try:
        logs = load_logs()
        logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": logs
        })
    except Exception as e:
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": [],
            "error": f"ログ読み込みエラー: {str(e)}"
        })
