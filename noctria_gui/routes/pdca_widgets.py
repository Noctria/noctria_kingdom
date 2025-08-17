# noctria_gui/routes/pdca_widgets.py
# -*- coding: utf-8 -*-
"""
PDCA ウィジェット群
- GET  /pdca/api/recent-adoptions        : JSON（直近採用タグ×Decision 突き合わせ）
- GET  /pdca/widgets/recent-adoptions    : HTMLフラグメント（レイアウト無しのカード群）
  - 他テンプレから `{% include %}` せずに <iframe> や hx-get（htmx等）で差し込める

既存の src/core/git_utils.py / src/core/decision_registry.py を利用。
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

try:
    from src.core.git_utils import GitHelper
except Exception:
    GitHelper = None  # type: ignore

try:
    from src.core.decision_registry import tail_ledger
except Exception:
    tail_ledger = None  # type: ignore

router = APIRouter(prefix="/pdca", tags=["PDCA", "Widgets"])


def _render_fragment(request: Request, template: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    html = env.get_template(template).render(request=request, **ctx)
    # layoutを持たないフラグメントとして返す
    return HTMLResponse(html)


def _build_index_by_tag(max_scan: int = 2000) -> Dict[str, Dict[str, str]]:
    """
    Decision Registry を走査して tag -> latest(decision_id, ts_utc, phase)
    """
    idx: Dict[str, Dict[str, str]] = {}
    if tail_ledger is None:
        return idx
    for r in tail_ledger(n=max_scan):
        try:
            extra = json.loads(r.get("extra_json") or "{}")
        except Exception:
            extra = {}
        tag = (extra.get("adopt_result") or {}).get("tag") or extra.get("tag")
        if not tag:
            continue
        cur = idx.get(tag)
        ts = r.get("ts_utc") or ""
        if cur is None or ts > (cur.get("ts_utc") or ""):
            idx[tag] = {
                "decision_id": r.get("decision_id") or "",
                "ts_utc": ts,
                "phase": r.get("phase") or "",
            }
    return idx


def _collect(pattern: Optional[str], limit: int) -> List[Dict[str, Any]]:
    tags: List[Dict[str, str]] = []
    if GitHelper is not None:
        try:
            gh = GitHelper()
            tags = gh.list_tags(pattern=pattern or None, limit=limit)
        except Exception:
            tags = []
    idx = _build_index_by_tag()
    out: List[Dict[str, Any]] = []
    for t in tags:
        name = t.get("name", "")
        out.append({
            "tag": name,
            "date": t.get("date", ""),
            "sha": t.get("sha", ""),
            "annotated": t.get("annotated", "false"),
            "decision": idx.get(name) or {},  # {decision_id, ts_utc, phase}
        })
    return out


@router.get("/api/recent-adoptions")
async def api_recent_adoptions(
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(12, ge=1, le=100),
):
    data = _collect(pattern, limit)
    return JSONResponse({"pattern": pattern or "", "limit": limit, "items": data})


@router.get("/widgets/recent-adoptions", response_class=HTMLResponse)
async def widget_recent_adoptions(
    request: Request,
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(12, ge=1, le=100),
    title: Optional[str] = Query("🧩 直近採用タグ"),
    cols: int = Query(3, ge=1, le=6, description="カードの横並び数（簡易CSSグリッド）"),
):
    items = _collect(pattern, limit)
    return _render_fragment(
        request,
        "widgets/recent_adoptions_fragment.html",
        title=title,
        items=items,
        pattern=pattern or "",
        limit=limit,
        cols=cols,
    )
