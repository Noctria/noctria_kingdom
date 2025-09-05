# noctria_gui/routes/statistics_routes.py
#!/usr/bin/env python3
# coding: utf-8
"""
📈 Statistics Detail (v1)
- /statistics/detail?mode={strategy|symbol}&key=...
- いまは strategy のみ対応。/pdca-dashboard/api/strategy_detail を叩いて表示
- テンプレ未配置や API 不在でも起動を止めないフェイルセーフ
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# テンプレート解決（path_config→フォールバック）
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]
try:
    from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # type: ignore
    _TPL_DIR = Path(str(NOCTRIA_GUI_TEMPLATES_DIR))
except Exception:
    _TPL_DIR = PROJECT_ROOT / "noctria_gui" / "templates"

templates = Jinja2Templates(directory=str(_TPL_DIR))
router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("/detail", response_class=HTMLResponse)
async def statistics_detail(
    request: Request,
    mode: str = Query("strategy"),
    key: str = Query(..., min_length=1),
    trace_id: Optional[str] = Query(None),
    decision_id: Optional[str] = Query(None),
):
    """
    詳細ページの土台。データ取得はクライアント側JSが /pdca-dashboard/api/... を叩く。
    """
    tpl = _TPL_DIR / "statistics_detail.html"
    if not tpl.exists():
        # テンプレが無い環境でも落ちない
        return JSONResponse(
            {
                "ok": True,
                "message": "statistics_detail.html not found (placeholder).",
                "hint": "noctria_gui/templates/statistics_detail.html を配置してください。",
                "params": {"mode": mode, "key": key, "trace_id": trace_id, "decision_id": decision_id},
            }
        )
    ctx: Dict[str, Any] = {
        "request": request,
        "mode": mode,
        "key": key,
        "trace_id": trace_id,
        "decision_id": decision_id,
    }
    return templates.TemplateResponse("statistics_detail.html", ctx)
