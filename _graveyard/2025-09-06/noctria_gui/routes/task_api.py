from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from . import task_manager   # ← ここを相対インポートに変更

router = APIRouter(prefix="/tasks", tags=["tasks"])

logger = logging.getLogger("task_api")

@router.get("/")
def list_tasks():
    try:
        tasks = task_manager.load_task_status()
        return JSONResponse(content=tasks)
    except Exception as e:
        logger.error(f"Failed to load task status: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to load task status"}, status_code=500)

@router.post("/{file_name}/status")
def update_status(file_name: str, status: str = Query(..., description="更新するステータス"), comment: Optional[str] = Query(None, description="コメント（任意）")):
    try:
        task_manager.update_task(file_name, status, comment)
        return {"message": "ステータス更新成功"}
    except Exception as e:
        logger.error(f"Failed to update task status for {file_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update status: {e}")
