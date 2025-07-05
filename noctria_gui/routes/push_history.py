from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# 📚 Git Push履歴をロードするサービス
from noctria_gui.services.push_history_service import load_push_logs

# 📂 テンプレートパス（共通管理）
from core.path_config import GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

# ========================================
# 📤 Git Push履歴ダッシュボード
#    - ソート順: asc（昇順）または desc（降順）
# ========================================
@router.get("/push-history", response_class=HTMLResponse)
async def show_push_history(request: Request, sort: str = "desc"):
    logs = load_push_logs()
    logs.sort(key=lambda x: x["timestamp"], reverse=(sort == "desc"))
    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
        "sort_order": sort,
    })
