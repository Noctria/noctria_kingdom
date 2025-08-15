# noctria_gui/routes/adoptions.py
# -*- coding: utf-8 -*-
"""
採用タグ（Git）× Decision Registry の突き合わせ集約ビュー
- GET  /adoptions            : 一覧（フィルタ/検索付き）
- GET  /adoptions.csv        : 同データのCSVエクスポート
- GET  /adoptions.json       : 同データのJSONエクスポート

既存の /tags, /pdca/recent-adoptions を横断して俯瞰するダッシュボード。
"""

from __future__ import annotations
import csv
import io
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse

try:
    from src.core.git_utils import GitHelper
except Exception:
    GitHelper = None  # type: ignore

try:
    from src.core.decision_registry import tail_ledger
except Exception:
    tail_ledger = None  # type: ignore

router = APIRouter(prefix="", tags=["PDCA", "Git"])


def _render(request: Request, template: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    return HTMLResponse(env.get_template(template).render(request=request, **ctx))


def _build_registry_index(max_scan: int = 5000) -> Dict[str, Dict[str, str]]:
    """
    Decision Registry を走査して tag -> {decision_id, ts_utc, phase} の最新だけを残す
    """
    idx: Dict[str, Dict[str, str]] = {}
    if tail_ledger is None:
        return idx
    rows = tail_ledger(n=max_scan)
    for r in rows:
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


def _collect_records(pattern: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """
    Git タグと Registry の突き合わせ済みレコードを生成
    """
    tags: List[Dict[str, str]] = []
    git_ok = False
    if GitHelper is not None:
        try:
            gh = GitHelper()
            tags = gh.list_tags(pattern=pattern or None, limit=limit)
            git_ok = True
        except Exception:
            git_ok = False

    idx = _build_registry_index()
    records: List[Dict[str, Any]] = []
    for t in tags:
        name = t.get("name", "")
        rec = {
            "tag": name,
            "date": t.get("date", ""),
            "sha": t.get("sha", ""),
            "annotated": t.get("annotated", "false"),
            "decision_id": "",
            "decision_ts_utc": "",
            "decision_phase": "",
        }
        d = idx.get(name)
        if d:
            rec.update(
                decision_id=d.get("decision_id", ""),
                decision_ts_utc=d.get("ts_utc", ""),
                decision_phase=d.get("phase", ""),
            )
        records.append(rec)
    return records


@router.get("/adoptions", response_class=HTMLResponse)
async def adoptions_index(
    request: Request,
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(200, ge=1, le=1000),
    q: Optional[str] = Query(None, description="free-text filter (tag/sha/decision_id/phase)"),
):
    rows = _collect_records(pattern=pattern, limit=limit)

    if q:
        ql = q.lower()
        def _hit(r: Dict[str, Any]) -> bool:
            return any(
                (str(r.get(k, "")) or "").lower().find(ql) >= 0
                for k in ("tag", "sha", "decision_id", "decision_phase")
            )
        rows = [r for r in rows if _hit(r)]

    return _render(
        request,
        "adoptions.html",
        page_title="🧩 PDCA — 採用タグ × Decision 一覧",
        pattern=pattern or "",
        limit=limit,
        q=q or "",
        rows=rows,
        registry_available=(tail_ledger is not None),
        git_available=(GitHelper is not None),
    )


@router.get("/adoptions.csv")
async def adoptions_csv(
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(200, ge=1, le=5000),
    q: Optional[str] = Query(None),
):
    rows = _collect_records(pattern=pattern, limit=limit)
    if q:
        ql = q.lower()
        rows = [
            r for r in rows
            if any((str(r.get(k, "")) or "").lower().find(ql) >= 0 for k in ("tag", "sha", "decision_id", "decision_phase"))
        ]

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["tag", "date", "sha", "annotated", "decision_id", "decision_ts_utc", "decision_phase"])
    w.writeheader()
    w.writerows(rows)
    data = buf.getvalue()
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="adoptions.csv"'},
    )


@router.get("/adoptions.json")
async def adoptions_json(
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(200, ge=1, le=5000),
    q: Optional[str] = Query(None),
):
    rows = _collect_records(pattern=pattern, limit=limit)
    if q:
        ql = q.lower()
        rows = [
            r for r in rows
            if any((str(r.get(k, "")) or "").lower().find(ql) >= 0 for k in ("tag", "sha", "decision_id", "decision_phase"))
        ]
    return JSONResponse(rows)
