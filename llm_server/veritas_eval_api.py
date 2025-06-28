from fastapi import APIRouter
import json
import os
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/veritas/eval_logs", response_class=JSONResponse)
def get_veritas_eval_logs():
    """
    📄 Veritasの戦略評価ログをJSONで返すAPI。
    GUI側から取得可能。
    """
    log_path = "/noctria_kingdom/airflow_docker/logs/veritas_eval_result.json"

    if not os.path.exists(log_path):
        return []

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            logs = json.load(f)
            return logs
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"ログ読み込み失敗: {str(e)}"}
        )
