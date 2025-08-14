# noctria_gui/routes/pdca_routes.py
#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca-dashboard - PDCAダッシュボードの画面表示ルート
- クエリパラメータからフィルタを受け取り、テンプレートに渡す
- 現時点ではダミーデータだが、今後の拡張でDBやログから取得可能
- テンプレートディレクトリは core.path_config の定数が無い場合でも安全にフォールバック
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ========================================
# 📁 テンプレートディレクトリ解決（安全なフォールバック）
# ========================================
_templates_dir: Optional[Path] = None
try:
    # プロジェクトで統一管理されている場合はこちらを優先
    from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # type: ignore
    _templates_dir = Path(str(NOCTRIA_GUI_TEMPLATES_DIR))
except Exception:
    # 直下の noctria_gui/templates をフォールバックとして使用
    _here = Path(__file__).resolve()
    _templates_dir = _here.parents[1] / "templates"

if not _templates_dir.exists():
    # 最後の保険：存在しない場合でも FastAPI 起動を止めない（後で 500 を返す）
    # ここでは例外にしない（開発初期のため）
    pass

templates = Jinja2Templates(directory=str(_templates_dir))

# ========================================
# ⚙️ ルーター設定
# ========================================
router = APIRouter(
    prefix="/pdca-dashboard",     # すべてのルートはこの接頭辞を持つ
    tags=["PDCA"]                 # FastAPI Swagger用タグ
)

# ========================================
# 🔎 フィルタ抽出ユーティリティ
# ========================================
def _parse_date(value: Optional[str]) -> Optional[str]:
    """YYYY-MM-DD の簡易検証。形式不正は None で返す（テンプレにそのまま渡さない）。"""
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None

def _extract_filters(request: Request) -> Dict[str, Any]:
    qp = request.query_params
    filters: Dict[str, Any] = {
        "strategy": qp.get("strategy", "").strip(),
        # 拡張用（必要になったらuncomment）
        "symbol": qp.get("symbol", "").strip() if qp.get("symbol") else "",
        "date_from": _parse_date(qp.get("date_from")),
        "date_to": _parse_date(qp.get("date_to")),
        # 勝率/最大DDなど数値系（将来のバリデーション前提で文字列保持）
        "winrate_diff_min": qp.get("winrate_diff_min"),
        "maxdd_diff_max": qp.get("maxdd_diff_max"),
        "search": qp.get("search"),
    }
    return filters

# ========================================
# 🔍 ダッシュボード表示ルート
# ========================================
@router.get("/", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    """
    PDCAダッシュボードのメインビュー。
    クエリパラメータからフィルターを取得し、テンプレートに渡す。
    """
    if not _templates_dir or not (_templates_dir / "pdca_dashboard.html").exists():
        # テンプレート未配置時の分かりやすいエラー
        return HTMLResponse(
            content=(
                "<h3>pdca_dashboard.html が見つかりません。</h3>"
                f"<p>探索ディレクトリ: {_templates_dir}</p>"
                "<p>noctria_gui/templates/pdca_dashboard.html を配置してください。</p>"
            ),
            status_code=500,
        )

    filters = _extract_filters(request)

    # 📦 PDCAデータ取得（現時点ではダミーデータ）
    # 将来: DB / data/pdca_logs/ 配下のCSV/JSONを集計してここに渡す
    pdca_data = [
        # 例:
        # {
        #     "strategy": "mean_revert_001",
        #     "win_rate": 72.5,
        #     "max_dd": 12.4,
        #     "timestamp": "2025-07-13T12:34:56",
        #     "tag": "recheck",
        #     "notes": ""
        # },
    ]

    return templates.TemplateResponse(
        "pdca_dashboard.html",
        {
            "request": request,
            "filters": filters,
            "pdca_logs": pdca_data,
        },
    )

# ========================================
# 🧪 ヘルスチェック/軽量データAPI（任意）
# ========================================
@router.get("/health", response_class=JSONResponse)
async def pdca_dashboard_health():
    return JSONResponse(
        {
            "ok": True,
            "templates_dir": str(_templates_dir) if _templates_dir else None,
            "template_exists": bool(_templates_dir and (_templates_dir / "pdca_dashboard.html").exists()),
            "message": "pdca-dashboard router is ready",
        }
    )
