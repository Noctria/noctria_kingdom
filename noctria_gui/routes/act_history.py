from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from datetime import datetime

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, DATA_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 🗂️ Actログディレクトリ
ACT_LOG_DIR = DATA_DIR / "act_logs"

@router.get("/act-history", response_class=HTMLResponse)
async def show_act_history(request: Request):
    act_files = sorted(ACT_LOG_DIR.glob("*.json"), reverse=True)
    act_logs = []

    for file in act_files:
        with open(file, "r", encoding="utf-8") as f:
            try:
                content = json.load(f)
                content["filename"] = file.name
                content["timestamp"] = extract_timestamp_from_filename(file.name)
                act_logs.append(content)
            except Exception as e:
                print(f"❌ JSON読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "act_logs": act_logs,
    })


def extract_timestamp_from_filename(name: str) -> str:
    """ファイル名から日時部分を抽出"""
    try:
        base = name.replace(".json", "")
        dt = datetime.strptime(base, "%Y-%m-%dT%H-%M-%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"
