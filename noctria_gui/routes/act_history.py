# routes/act_history.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import json
from typing import List, Optional
from core.path_config import ACT_LOG_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(Path("noctria_gui/templates")))

def load_act_logs() -> List[dict]:
    logs = []
    if ACT_LOG_DIR.exists():
        for file in sorted(ACT_LOG_DIR.glob("*.json")):
            with open(file, "r", encoding="utf-8") as f:
                log = json.load(f)
                log["__filename"] = file.name
                logs.append(log)
    return logs

@router.get("/act-history", response_class=HTMLResponse)
async def show_act_history(
    request: Request,
    strategy: Optional[str] = None,
    pushed: Optional[str] = None,
    sort_by: Optional[str] = "timestamp",
    order: Optional[str] = "desc"
):
    logs = load_act_logs()

    # フィルタリング
    if strategy:
        logs = [log for log in logs if strategy.lower() in log.get("strategy", "").lower()]
    if pushed == "true":
        logs = [log for log in logs if log.get("pushed") is True]
    elif pushed == "false":
        logs = [log for log in logs if log.get("pushed") is False]

    # ソート
    reverse = (order == "desc")
    if sort_by == "timestamp":
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=reverse)
    elif sort_by == "strategy":
        logs.sort(key=lambda x: x.get("strategy", ""), reverse=reverse)

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "strategy": strategy,
        "pushed": pushed,
        "sort_by": sort_by,
        "order": order,
    })

@router.post("/act-history/push")
async def push_strategy_log(request: Request):
    form = await request.form()
    filename = form.get("filename")
    if not filename:
        return RedirectResponse(url="/act-history", status_code=303)

    filepath = ACT_LOG_DIR / filename
    if not filepath.exists():
        return RedirectResponse(url="/act-history", status_code=303)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 署名付きで Git Push 処理（省略・外部スクリプトと連携可能）
    print(f"📤 Push中...: {data['strategy']}")

    # pushed フラグ更新
    data["pushed"] = True
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Git操作ログ保存（オプション）
    push_log_dir = Path("data/push_logs")
    push_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = push_log_dir / f"{data['strategy'].replace('.py','')}_{data['timestamp'].replace(':','-')}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "strategy": data["strategy"],
            "timestamp": data["timestamp"],
            "status": "pushed",
            "note": "GUIからPushされた記録"
        }, f, indent=2, ensure_ascii=False)

    return RedirectResponse(url="/act-history", status_code=303)

@router.post("/act-history/force-record")
async def force_record_strategy(request: Request):
    form = await request.form()
    strategy_name = form.get("strategy")
    score = json.loads(form.get("score", "{}"))
    reason = form.get("reason", "再評価により強制昇格")

    timestamp = datetime.utcnow().replace(microsecond=0).isoformat()

    act_log = {
        "timestamp": timestamp,
        "strategy": strategy_name,
        "score": score,
        "reason": reason,
        "pushed": False,
        "forced": True
    }

    ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{strategy_name.replace('.py','')}_{timestamp.replace(':','-')}.json"
    out_path = ACT_LOG_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(act_log, f, indent=2, ensure_ascii=False)

    return RedirectResponse(url="/act-history", status_code=303)
