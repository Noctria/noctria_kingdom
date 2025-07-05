from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import status
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
import json
from datetime import datetime

from core.path_config import DATA_DIR, GUI_TEMPLATES_DIR
from tools.push_official_strategy_to_github import git_push_official_strategies

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

ACT_LOG_DIR = DATA_DIR / "act_logs"

def load_act_logs(pushed_filter=None):
    logs = []
    for path in sorted(ACT_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["path"] = str(path)
                if pushed_filter is None or data.get("pushed", False) == pushed_filter:
                    logs.append(data)
        except Exception as e:
            print(f"❌ ログ読み込み失敗: {path} - {e}")
    return logs

@router.get("/act-history")
def show_act_history(request: Request, pushed: str = None):
    if pushed == "true":
        logs = load_act_logs(pushed_filter=True)
    elif pushed == "false":
        logs = load_act_logs(pushed_filter=False)
    else:
        logs = load_act_logs()

    message = request.session.pop("flash_message", None)

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "flash_message": message
    })

@router.post("/act-history/push")
def push_strategy_to_github(request: Request, log_path: str = Form(...)):
    log_path = Path(log_path)

    if not log_path.exists():
        request.session["flash_message"] = "❌ 指定されたログファイルが存在しません"
        return RedirectResponse(url="/act-history", status_code=status.HTTP_302_FOUND)

    # ログ読み込み
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        request.session["flash_message"] = f"❌ ログ読み込み失敗: {e}"
        return RedirectResponse(url="/act-history", status_code=status.HTTP_302_FOUND)

    # GitHub push 実行
    try:
        git_push_official_strategies()
        data["pushed"] = True
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        request.session["flash_message"] = f"🚀 GitHubに戦略をPushしました: {data['strategy']}"
    except Exception as e:
        request.session["flash_message"] = f"❌ GitHub Push失敗: {e}"

    return RedirectResponse(url="/act-history", status_code=status.HTTP_302_FOUND)
