# noctria_gui/routes/git_tags.py
# -*- coding: utf-8 -*-
"""
Gitタグ一覧 + Decision Registry 突き合わせビュー
- GET  /tags                 : タグ一覧（パターン/件数フィルタ）
- GET  /tags/{tag}           : タグ詳細 + 関連Decision表示
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse

# Gitヘルパ
try:
    from src.core.git_utils import GitHelper
except Exception:
    GitHelper = None  # type: ignore

# Decision Registry（CSV）
try:
    from src.core.decision_registry import tail_ledger, list_events
except Exception:
    tail_ledger = None  # type: ignore
    list_events = None  # type: ignore

router = APIRouter(prefix="", tags=["Git"])

def _render(request: Request, template: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    return HTMLResponse(env.get_template(template).render(**ctx))

def _find_related_decisions_by_tag(tag: str, max_scan: int = 1000) -> List[Dict[str, Any]]:
    """
    decision_registry の CSV 末尾から走査して、extra_json に tag を含むものを抽出
    """
    if tail_ledger is None:
        return []
    rows = tail_ledger(n=max_scan)
    related: List[Dict[str, Any]] = []
    for r in rows:
        try:
            extra = json.loads(r.get("extra_json") or "{}")
        except Exception:
            extra = {}
        # adopt_and_push の戻りに { "tag": tag } が入っている想定
        tag_in_extra = extra.get("adopt_result", {}).get("tag") or extra.get("tag")
        if tag_in_extra == tag:
            related.append(r)
    # 新しい順に
    related.sort(key=lambda x: x.get("ts_utc") or "", reverse=True)
    return related

@router.get("/tags", response_class=HTMLResponse)
async def tags_index(
    request: Request,
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(200, ge=1, le=500),
):
    if GitHelper is None:
        return HTMLResponse("<h1>GitHelper 未配備</h1><p>src/core/git_utils.py を配置してください。</p>", status_code=501)
    gh = GitHelper()
    tags = gh.list_tags(pattern=pattern or None, limit=limit)
    return _render(
        request,
        "git_tags.html",
        page_title="🏷 Git Tags",
        mode="index",
        pattern=pattern or "",
        limit=limit,
        tags=tags,
    )

@router.get("/tags/{tag}", response_class=HTMLResponse)
async def tag_detail(
    request: Request,
    tag: str,
):
    if GitHelper is None:
        return HTMLResponse("<h1>GitHelper 未配備</h1><p>src/core/git_utils.py を配置してください。</p>", status_code=501)
    gh = GitHelper()
    try:
        info = gh.get_tag_detail(tag)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"tag not found: {tag} ({e})")

    related: List[Dict[str, Any]] = _find_related_decisions_by_tag(tag)
    return _render(
        request,
        "git_tags.html",
        page_title=f"🏷 Tag: {tag}",
        mode="detail",
        tag=tag,
        info=info,
        related=related,
        registry_available=tail_ledger is not None,
    )
