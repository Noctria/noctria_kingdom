from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from datetime import datetime
from core.path_config import PDCA_LOG_DIR, GUI_TEMPLATES_DIR, STRATEGIES_DIR, DATA_DIR
from scripts.github_push import push_single_strategy_to_github

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

ACT_LOG_DIR = DATA_DIR / "act_logs" / "veritas_act"
GIT_PUSH_LOG_DIR = DATA_DIR / "act_logs" / "git_push_history"
ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)
GIT_PUSH_LOG_DIR.mkdir(parents=True, exist_ok=True)

def load_act_logs(date_filter=None, strategy_filter=None, only_unpushed=False):
    logs = []
    for path in sorted(ACT_LOG_DIR.glob("*.json"), reverse=True):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["file_path"] = str(path)
        if date_filter and not data["timestamp"].startswith(date_filter):
            continue
        if strategy_filter and data["strategy"] != strategy_filter:
            continue
        if only_unpushed and data.get("pushed") is True:
            continue
        logs.append(data)
    return logs

def save_git_push_log(strategy_name: str, log_path: str, result: str, details: str):
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log = {
        "timestamp": timestamp,
        "strategy": strategy_name,
        "log_path": log_path,
        "result": result,
        "details": details,
        "pushed_by": "system"
    }
    filepath = GIT_PUSH_LOG_DIR / f"{timestamp}_push.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

@router.get("/act-history")
async def act_history(request: Request, date: str = None, strategy: str = None, unpushed: bool = False):
    logs = load_act_logs(date_filter=date, strategy_filter=strategy, only_unpushed=unpushed)
    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "date_filter": date,
        "strategy_filter": strategy,
        "only_unpushed": unpushed
    })

@router.post("/act-history/push")
async def push_strategy(request: Request, log_path: str = Form(...)):
    path = Path(log_path)
    if not path.exists():
        return RedirectResponse("/act-history", status_code=302)

    with open(path, "r", encoding="utf-8") as f:
        log_data = json.load(f)

    strategy_name = log_data.get("strategy")
    strategy_path = STRATEGIES_DIR / "official" / strategy_name

    if not strategy_path.exists():
        print(f"❌ 戦略ファイルが存在しません: {strategy_path}")
        return RedirectResponse("/act-history", status_code=302)

    try:
        push_result = push_single_strategy_to_github(strategy_path)
        log_data["pushed"] = True
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        save_git_push_log(
            strategy_name=strategy_name,
            log_path=str(path),
            result="success",
            details=f"GitHubにpush成功: 🤖 Veritas戦略をofficialに自動反映（{datetime.now().date()}）"
        )

    except Exception as e:
        save_git_push_log(
            strategy_name=strategy_name,
            log_path=str(path),
            result="failure",
            details=str(e)
        )
        print(f"❌ GitHubへのpushに失敗しました: {e}")

    return RedirectResponse("/act-history", status_code=302)
