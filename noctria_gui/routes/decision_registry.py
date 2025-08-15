# noctria_gui/routes/decision_registry.py
# -*- coding: utf-8 -*-
"""
Decision Registry ビュー（HUD）
- GET /decisions            : 直近イベントの一覧（CSV tail）
- GET /decisions/{decision}: 該当 decision_id のイベント時系列
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

try:
    # src側のレジストリ
    from src.core.decision_registry import tail_ledger, list_events
except Exception as e:  # フォールバック（未配置でもGUIは生かす）
    tail_ledger = None  # type: ignore
    list_events = None  # type: ignore

router = APIRouter(prefix="", tags=["Decisions"])

def _render(request: Request, template_name: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    tmpl = env.get_template(template_name)
    html = tmpl.render(**ctx)
    return HTMLResponse(html)

@router.get("/decisions", response_class=HTMLResponse)
async def decisions_index(request: Request, n: int = 200, q: Optional[str] = None):
    """
    直近 n 件のイベントを一覧表示。q があれば decision_id/kind/phase/issued_by に含まれるものをフィルタ。
    """
    if tail_ledger is None:
        return HTMLResponse("<h1>Decision Registry 未配備</h1><p>src/core/decision_registry.py を配置してください。</p>", status_code=501)

    rows: List[Dict[str, Any]] = tail_ledger(n=n)  # JSON文字列のまま返る想定
    if q:
        ql = q.lower()
        def _hit(r: Dict[str, str]) -> bool:
            return any(
                (r.get(k, "") or "").lower().find(ql) >= 0
                for k in ("decision_id", "kind", "phase", "issued_by")
            )
        rows = [r for r in rows if _hit(r)]

    return _render(
        request,
        "decision_registry.html",
        page_title="🗂 Decision Registry",
        mode="index",
        query=q or "",
        rows=rows,
        n=n,
    )

@router.get("/decisions/{decision_id}", response_class=HTMLResponse)
async def decisions_detail(request: Request, decision_id: str):
    """
    指定 decision_id のイベント時系列を表示
    """
    if list_events is None:
        return HTMLResponse("<h1>Decision Registry 未配備</h1><p>src/core/decision_registry.py を配置してください。</p>", status_code=501)

    events = list_events(decision_id=decision_id)  # JSON文字列のまま
    if not events:
        raise HTTPException(status_code=404, detail="decision not found")

    # 最新イベントを簡易まとめ
    latest = events[-1] if events else {}
    try:
        intent = json.loads(latest.get("intent_json", "{}"))
    except Exception:
        intent = {}
    try:
        extra = json.loads(latest.get("extra_json", "{}"))
    except Exception:
        extra = {}

    return _render(
        request,
        "decision_registry.html",
        page_title=f"🗂 Decision: {decision_id}",
        mode="detail",
        decision_id=decision_id,
        events=events,
        latest=latest,
        latest_intent=intent,
        latest_extra=extra,
    )
