from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
import task_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/")
def list_tasks():
    return JSONResponse(content=task_manager.load_task_status())

@router.post("/{file_name}/status")
def update_status(file_name: str, status: str = Query(...), comment: Optional[str] = None):
    task_manager.update_task(file_name, status, comment)
    return {"message": "ステータス更新成功"}
