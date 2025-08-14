# noctria_gui/routes/pdca_routes.py
#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca-dashboard - PDCAダッシュボードの画面表示ルート
- クエリパラメータからフィルタを受け取り、テンプレートに渡す
- いまはダミーデータ、将来は DB / ログを集計して表示
- テンプレートディレクトリは path_config 不在でも安全にフォールバック

補足:
- このファイルは /pdca-dashboard の最小ビューを提供します。
  既存の /pdca/summary（統計/CSV/API/再評価トリガ等）が別ルーターにある場合は共存可能です。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ========================================
# 📁 テンプレートディレクトリ解決（安全フォールバック）
# ========================================
def _resolve_templates_dir() -> Path:
    """
    テンプレートディレクトリの解決を行う。
    - 優先: src.core.path_config.NOCTRIA_GUI_TEMPLATES_DIR
    - 次点: core.path_config.NOCTRIA_GUI_TEMPLATES_DIR（古いimport形）
    - 最後: このファイルの 2 つ上(noctria_gui/) 配下の templates/
    """
    # 1) src.core.path_config（推奨）
    try:
        from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR as _TPL  # type: ignore
        p = Path(str(_TPL))
        if p.exists():
            return p
    except Exception:
        pass

    # 2) core.path_config（互換）
    try:
        from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR as _TPL  # type: ignore
        p = Path(str(_TPL))
        if p.exists():
            return p
    except Exception:
        pass

    # 3) フォールバック: <repo_root>/noctria_gui/templates
    here = Path(__file__).resolve()
    fallback = here.parents[1] / "templates"
    return fallback

_TEMPLATES_DIR = _resolve_templates_dir()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ========================================
# ⚙️ ルーター設定
# ========================================
router = APIRouter(
    prefix="/pdca-dashboard",
    tags=["PDCA"]
)

# ========================================
# 🔎 フィルタ抽出ユーティリティ
# ========================================
def _parse_date(value: Optional[str]) -> Optional[str]:
    """YYYY-MM-DD の簡易検証。形式不正は None を返す。"""
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
        "strategy": (qp.get("strategy") or "").strip(),
        # 拡張用
        "symbol": (qp.get("symbol") or "").strip(),
        "date_from": _parse_date(qp.get("date_from")),
        "date_to": _parse_date(qp.get("date_to")),
        # 数値系（UI入力の生文字列を保持しつつテンプレへ渡す）
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
    tpl = _TEMPLATES_DIR / "pdca_dashboard.html"
    if not tpl.exists():
        # テンプレート未配置時の分かりやすいエラー
        return HTMLResponse(
            content=(
                "<h3>pdca_dashboard.html が見つかりません。</h3>"
                f"<p>探索ディレクトリ: {_TEMPLATES_DIR}</p>"
                "<p>noctria_gui/templates/pdca_dashboard.html を配置してください。</p>"
            ),
            status_code=500,
        )

    filters = _extract_filters(request)

    # 📦 PDCAデータ取得（現時点ではダミー）
    # 将来: data/pdca_logs/ 配下CSV/JSON or DBからの集計結果をここへ
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
# 🩺 ヘルスチェック/軽量データAPI
# ========================================
@router.get("/health", response_class=JSONResponse)
async def pdca_dashboard_health():
    return JSONResponse(
        {
            "ok": True,
            "templates_dir": str(_TEMPLATES_DIR),
            "template_exists": (_TEMPLATES_DIR / "pdca_dashboard.html").exists(),
            "message": "pdca-dashboard router is ready",
        }
    )

# ---- ここから追記 ---------------------------------------------------------

@router.get("/api/recent", response_model=Dict[str, Any])
def api_recent(limit: int = Query(20, ge=1, le=100)):
    """
    直近の評価を N 件だけ返す（表表示用の軽量API）
    """
    df = _read_logs_dataframe()
    if df.empty:
        return {"rows": []}

    cols = [
        "evaluated_at", "strategy", "tag",
        "winrate_old", "winrate_new", "winrate_diff",
        "maxdd_old", "maxdd_new", "maxdd_diff",
        "trades_old", "trades_new", "notes",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    dff = df.sort_values("evaluated_at", ascending=False).head(limit)
    # 文字列化して安全に返す
    dff["evaluated_at"] = dff["evaluated_at"].astype(str)
    return {"rows": dff[cols].to_dict(orient="records")}


@router.get("/api/strategy_detail", response_model=Dict[str, Any])
def api_strategy_detail(strategy: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=500)):
    """
    指定戦略の履歴詳細（最新 limit 件）
    """
    df = _read_logs_dataframe()
    if df.empty:
        return {"strategy": strategy, "rows": []}

    dff = df[df["strategy"].astype(str) == strategy].copy()
    if dff.empty:
        return {"strategy": strategy, "rows": []}

    cols = [
        "evaluated_at", "strategy", "tag",
        "winrate_old", "winrate_new", "winrate_diff",
        "maxdd_old", "maxdd_new", "maxdd_diff",
        "trades_old", "trades_new", "notes", "__source_file",
    ]
    for c in cols:
        if c not in dff.columns:
            dff[c] = None

    dff = dff.sort_values("evaluated_at", ascending=False).head(limit)
    dff["evaluated_at"] = dff["evaluated_at"].astype(str)
    return {"strategy": strategy, "rows": dff[cols].to_dict(orient="records")}
# ---- 追記ここまで ---------------------------------------------------------
