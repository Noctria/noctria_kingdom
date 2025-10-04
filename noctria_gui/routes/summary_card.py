#!/usr/bin/env python3
# coding: utf-8
# [NOCTRIA_CORE_REQUIRED]
"""
GUI: PDCA 三行要約カード表示ルート
- /pdca/summary_card?trace_id=... : 単一カード表示（trace_id 省略可 → 最新1件を自動表示）
- /pdca/summary_recent?limit=10   : 直近N件のカード一覧
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# ルート推定（プロジェクト直下に pdca_log.db がある前提）
ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "pdca_log.db"

# テンプレート
TEMPLATES_DIR = ROOT / "noctria_gui" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["PDCA Summary"])


def _row_to_item(row) -> Dict[str, Any]:
    _id, created_at, trace_id, source_path, model_used, summary_json = row
    arr = json.loads(summary_json)
    if not (isinstance(arr, list) and len(arr) == 3 and all(isinstance(x, str) for x in arr)):
        raise HTTPException(status_code=500, detail="invalid summary_json format")
    return {
        "id": _id,
        "created_at": created_at,
        "trace_id": trace_id,
        "source_path": source_path,
        "model_used": model_used or "",
        "lines": arr,
    }


def _fetch_by_trace_id(trace_id: str) -> Dict[str, Any]:
    if not SQLITE_PATH.exists():
        raise HTTPException(status_code=500, detail=f"SQLite not found: {SQLITE_PATH}")
    q = """
    SELECT id, created_at, trace_id, source_path, model_used, summary_json
      FROM pdca_summaries
     WHERE trace_id = ?
     ORDER BY id DESC
     LIMIT 1
    """
    con = sqlite3.connect(str(SQLITE_PATH))
    try:
        cur = con.cursor()
        row = cur.execute(q, (trace_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"summary not found for trace_id={trace_id}"
            )
        return _row_to_item(row)
    finally:
        con.close()


def _fetch_latest_one() -> Dict[str, Any]:
    if not SQLITE_PATH.exists():
        raise HTTPException(status_code=500, detail=f"SQLite not found: {SQLITE_PATH}")
    q = """
    SELECT id, created_at, trace_id, source_path, model_used, summary_json
      FROM pdca_summaries
     ORDER BY id DESC
     LIMIT 1
    """
    con = sqlite3.connect(str(SQLITE_PATH))
    try:
        cur = con.cursor()
        row = cur.execute(q).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="no summary rows yet")
        return _row_to_item(row)
    finally:
        con.close()


def _fetch_recent(limit: int = 10) -> List[Dict[str, Any]]:
    if not SQLITE_PATH.exists():
        return []
    q = f"""
    SELECT id, created_at, trace_id, source_path, model_used, summary_json
      FROM pdca_summaries
     ORDER BY id DESC
     LIMIT {int(limit)}
    """
    con = sqlite3.connect(str(SQLITE_PATH))
    try:
        cur = con.cursor()
        rows = cur.execute(q).fetchall()
    finally:
        con.close()

    out: List[Dict[str, Any]] = []
    for row in rows:
        try:
            out.append(_row_to_item(row))
        except Exception:
            continue
    return out


@router.get("/pdca/summary_card", response_class=HTMLResponse)
def summary_card(
    request: Request, trace_id: Optional[str] = Query(None, description="PDCA trace_id (省略可)")
):
    # trace_id が無ければ最新1件を採用
    data = _fetch_by_trace_id(trace_id) if trace_id else _fetch_latest_one()
    return templates.TemplateResponse(
        "pdca/summary_card.html",
        {"request": request, "item": data, "title": "PDCA 三行要約"},
    )


@router.get("/pdca/summary_recent", response_class=HTMLResponse)
def summary_recent(request: Request, limit: int = Query(10, ge=1, le=100)):
    items = _fetch_recent(limit)
    return templates.TemplateResponse(
        "pdca/summary_recent.html",
        {"request": request, "items": items, "title": "PDCA 三行要約（直近）", "limit": limit},
    )
