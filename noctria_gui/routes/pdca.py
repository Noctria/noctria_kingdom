from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os
import json
import requests

from core.path_config import (
    PDCA_LOG_DIR,
    NOCTRIA_GUI_TEMPLATES_DIR,
    STRATEGIES_VERITAS_GENERATED_DIR,
)

from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
AIRFLOW_API_USER = os.getenv("AIRFLOW_API_USER", "admin")
AIRFLOW_API_PASSWORD = os.getenv("AIRFLOW_API_PASSWORD", "admin")

# ================================
# 🔍 PDCAログ一覧表示
# ================================
@router.get("/pdca", response_class=HTMLResponse)
async def show_pdca_dashboard(
    request: Request,
    strategy: str = Query(default=None),
    symbol: str = Query(default=None),
    signal: str = Query(default=None),
    tag: str = Query(default=None),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    sort: str = Query(default=None),
):
    logs = []
    tag_set = set()

    for log_file in sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ ログ読み込み失敗: {log_file} -> {e}")
            continue

        ts = data.get("timestamp", "")
        try:
            ts_dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            ts_dt = None

        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tag_set.update(tags)

        logs.append({
            "filename": log_file.name,
            "path": str(log_file),
            "strategy": data.get("strategy", "N/A"),
            "timestamp": ts,
            "timestamp_dt": ts_dt,
            "signal": data.get("signal", "N/A"),
            "symbol": data.get("symbol", "N/A"),
            "lot": data.get("lot", "N/A"),
            "tp": data.get("tp", "N/A"),
            "sl": data.get("sl", "N/A"),
            "win_rate": data.get("win_rate"),
            "max_dd": data.get("max_dd"),
            "trades": data.get("trades"),
            "tags": tags,
            "json_text": json.dumps(data, indent=2, ensure_ascii=False),
        })

    def matches(log):
        if strategy and strategy.lower() not in log["strategy"].lower():
            return False
        if symbol and symbol != log["symbol"]:
            return False
        if signal and signal != log["signal"]:
            return False
        if tag and tag not in log["tags"]:
            return False
        if date_from:
            try:
                from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] < from_dt:
                    return False
            except Exception:
                pass
        if date_to:
            try:
                to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] > to_dt:
                    return False
            except Exception:
                pass
        return True

    filtered_logs = [log for log in logs if matches(log)]

    if sort:
        reverse = sort.startswith("-")
        key = sort.lstrip("-")
        if key in ["win_rate", "max_dd", "trades", "timestamp_dt"]:
            filtered_logs.sort(key=lambda x: x.get(key) or 0, reverse=reverse)

    def make_json_serializable(log):
        new_log = log.copy()
        for key in ["timestamp_dt"]:
            val = new_log.get(key)
            if isinstance(val, datetime):
                new_log[key] = val.isoformat()
        tags = new_log.get("tags")
        if isinstance(tags, str):
            new_log["tags"] = [tags]
        return new_log

    logs_serializable = [make_json_serializable(log) for log in filtered_logs]

    return templates.TemplateResponse("pdca_history.html", {
        "request": request,
        "logs": logs_serializable,
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "signal": signal or "",
            "tag": tag or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
        },
        "sort": sort or "",
        "available_tags": sorted(tag_set),
    })


# ================================
# 🔁 ログから注文を再実行
# ================================
@router.post("/pdca/replay")
async def replay_order_from_log(log_path: str = Form(...)):
    dag_id = "veritas_replay_dag"
    payload = {"conf": {"log_path": log_path}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns",
            json=payload,
            headers=headers,
            auth=(AIRFLOW_API_USER, AIRFLOW_API_PASSWORD)
        )

        if response.status_code in [200, 201]:
            print(f"✅ DAG起動成功: {log_path}")
            return RedirectResponse(url="/pdca", status_code=303)
        else:
            print(f"❌ DAGトリガー失敗: {response.text}")
            return JSONResponse(status_code=500, content={"detail": "DAG起動に失敗しました"})

    except Exception as e:
        print(f"❌ DAG通信エラー: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ================================
# 🔁 単一戦略の再評価
# ================================
@router.post("/pdca/recheck")
async def trigger_strategy_recheck(strategy_id: str = Form(...)):
    dag_id = "recheck_dag"
    payload = {"conf": {"strategy_id": strategy_id}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns",
            json=payload,
            headers=headers,
            auth=(AIRFLOW_API_USER, AIRFLOW_API_PASSWORD)
        )

        if response.status_code in [200, 201]:
            print(f"✅ 再評価DAG起動成功: {strategy_id}")
            return RedirectResponse(url="/pdca", status_code=303)
        else:
            print(f"❌ 再評価DAG失敗: {response.text}")
            return JSONResponse(status_code=500, content={"detail": "再評価に失敗しました"})

    except Exception as e:
        print(f"❌ 通信エラー: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ================================
# 🔁 全戦略一括再評価
# ================================
@router.post("/pdca/recheck_all")
async def trigger_all_strategy_rechecks():
    dag_id = "recheck_dag"
    headers = {"Content-Type": "application/json"}
    strategy_dir = STRATEGIES_VERITAS_GENERATED_DIR

    triggered = []
    errors = []

    for strategy_file in strategy_dir.glob("*.py"):
        strategy_id = strategy_file.stem
        payload = {"conf": {"strategy_id": strategy_id}}

        try:
            response = requests.post(
                f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns",
                json=payload,
                headers=headers,
                auth=(AIRFLOW_API_USER, AIRFLOW_API_PASSWORD)
            )

            if response.status_code in [200, 201]:
                print(f"✅ 起動: {strategy_id}")
                triggered.append(strategy_id)
            else:
                print(f"❌ 失敗: {strategy_id} -> {response.text}")
                errors.append({"strategy": strategy_id, "error": response.text})

        except Exception as e:
            print(f"❌ 通信エラー: {strategy_id} -> {e}")
            errors.append({"strategy": strategy_id, "error": str(e)})

    return JSONResponse({
        "status": "completed",
        "triggered_count": len(triggered),
        "triggered": triggered,
        "errors": errors,
    })
