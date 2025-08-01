from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from routes import chat_history_api, chat_api  # 追記でchat_apiをimport
import os

app = FastAPI()

app.include_router(chat_history_api.router)
app.include_router(chat_api.router)  # チャットAPIルーターを追加

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # 対話履歴表示画面（旧トップページ）
    return templates.TemplateResponse("chat_history.html", {"request": request})

@app.get("/chat_ui", response_class=HTMLResponse)
async def chat_ui(request: Request):
    # 双方向チャットUI画面追加
    return templates.TemplateResponse("chat_ui.html", {"request": request})
