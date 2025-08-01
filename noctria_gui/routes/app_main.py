import os
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

# 相対インポートに修正（または sys.path に親ディレクトリを追加）
from . import chat_history_api, chat_api

# ロガー設定
logger = logging.getLogger("noctria_logger")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = FastAPI()

app.include_router(chat_history_api.router)
app.include_router(chat_api.router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception: {exc}\nTraceback:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": "サーバー内部エラーが発生しました。管理者にお問い合わせください。"}
    )

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("chat_history.html", {"request": request})

@app.get("/chat_ui", response_class=HTMLResponse)
async def chat_ui(request: Request):
    return templates.TemplateResponse("chat_ui.html", {"request": request})
