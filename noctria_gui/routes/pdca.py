from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services.airflow_trigger import trigger_dag
from pathlib import Path
import json

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")
templates.env.filters["from_json"] = lambda x: json.loads(x)

# 📁 PDCAログ格納ディレクトリ
PDCA_LOG_DIR = Path("logs/pdca")

# =============================
# 🧩 ログ読み込み（履歴取得）
# =============================
def load_pdca_logs():
    histories = []
    for subdir in sorted(PDCA_LOG_DIR.iterdir(), reverse=True):
        if subdir.is_dir():
            for file in subdir.glob("*.json"):
                try:
                    content = json.loads(file.read_text(encoding="utf-8"))
                except Exception as e:
                    content = {"error": f"読み込み失敗: {e}"}
                histories.append({
                    "id": subdir.name,
                    "filename": file.name,
                    "content": content
                })
    return histories

# =============================
# 📺 GET: ダッシュボード表示
# =============================
@router.get("/pdca", response_class=HTMLResponse)
def dashboard(request: Request):
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": None
    })

# =============================
# ⚙️ POST: 全体PDCA実行（通常）
# =============================
@router.post("/pdca", response_class=HTMLResponse)
def trigger_pdca(request: Request):
    result = trigger_dag("veritas_pdca_dag")
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": f"通常実行: {result}"
    })

# =============================
# 📤 POST: 特定命令の再実行
# =============================
@router.post("/pdca/replay", response_class=HTMLResponse)
def replay_pdca(request: Request, filename: str = Form(...)):
    # 🔍 ファイル検索
    found = None
    for subdir in PDCA_LOG_DIR.iterdir():
        file_path = subdir / filename
        if file_path.exists():
            found = file_path
            break

    if not found:
        histories = load_pdca_logs()
        return templates.TemplateResponse("pdca_dashboard.html", {
            "request": request,
            "histories": histories,
            "message": f"❌ 再実行失敗: {filename} が見つかりませんでした"
        })

    # ✅ DAGにXCom/変数として渡す処理（将来的に拡張）
    result = trigger_dag("veritas_pdca_dag")  # TODO: 内容を反映させる場合は Airflow Variable or XCom の活用が必要

    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": f"📤 {filename} を再実行しました → {result}"
    })
