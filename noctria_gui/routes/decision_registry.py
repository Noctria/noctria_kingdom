# noctria_gui/routes/decision_registry.py
# -*- coding: utf-8 -*-
"""
Decision Registry ビュー（HUD）
- GET /decisions            : 直近イベントの一覧（CSV tail）
- GET /decisions/{decision}: 該当 decision_id のイベント時系列
- 追加: Airflow Run への相互リンク（extra_json に dag_run_id / dag_id を含む場合）
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

try:
    # src側のレジストリ
    from src.core.decision_registry import tail_ledger, list_events
except Exception:  # フォールバック（未配置でもGUIは生かす）
    tail_ledger = None  # type: ignore
    list_events = None  # type: ignore

router = APIRouter(prefix="", tags=["Decisions"])

def _render(request: Request, template_name: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    tmpl = env.get_template(template_name)
    html = tmpl.render(request=request, **ctx)  # ← request を渡す（トースト等で利用）
    return HTMLResponse(html)

def _extract_airflow_refs_from_extra(extra: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    extra_json から Airflow の (dag_id, dag_run_id) 候補を抽出する。
    想定される形:
      - {"dag_id": "...", "dag_run_id": "..."}
      - {"airflow": {"dag_id": "...", "dag_run_id": "..."}}
      - {"dag_run_id": "..."} のみ（dag_idは不明）
      - {"conf": {"dag_id": "...", ...}} のような埋め込み（best effort）
    """
    out: List[Tuple[str, str]] = []
    if not isinstance(extra, dict):
        return out

    # 直接キー
    dag_id = str(extra.get("dag_id") or "") or None
    run_id = str(extra.get("dag_run_id") or extra.get("run_id") or "") or None
    if run_id:
        out.append((dag_id or "", run_id))

    # airflow ネスト
    af = extra.get("airflow")
    if isinstance(af, dict):
        dag_id2 = str(af.get("dag_id") or "") or dag_id or ""
        run_id2 = str(af.get("dag_run_id") or af.get("run_id") or "") or ""
        if run_id2:
            out.append((dag_id2, run_id2))

    # conf ネスト
    conf = extra.get("conf")
    if isinstance(conf, dict):
        dag_id3 = str(conf.get("dag_id") or "") or (dag_id or "")
        run_id3 = str(conf.get("dag_run_id") or conf.get("run_id") or "") or ""
        if run_id3:
            out.append((dag_id3, run_id3))

    # 去重
    uniq = []
    seen = set()
    for d, r in out:
        key = (d or "", r or "")
        if key not in seen and r:
            uniq.append(key)
            seen.add(key)
    return uniq

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
    指定 decision_id のイベント時系列を表示 + Airflow Run への相互リンク
    """
    if list_events is None:
        return HTMLResponse("<h1>Decision Registry 未配備</h1><p>src/core/decision_registry.py を配置してください。</p>", status_code=501)

    events = list_events(decision_id=decision_id)  # JSON文字列のまま
    if not events:
        raise HTTPException(status_code=404, detail="decision not found")

    latest = events[-1] if events else {}
    try:
        intent = json.loads(latest.get("intent_json", "{}"))
    except Exception:
        intent = {}
    try:
        extra_latest = json.loads(latest.get("extra_json", "{}"))
    except Exception:
        extra_latest = {}

    # すべてのイベントから Airflow 参照を抽出
    airflow_refs: List[Dict[str, str]] = []
    seen = set()
    for ev in events:
        try:
            ex = json.loads(ev.get("extra_json") or "{}")
        except Exception:
            ex = {}
        for dag_id, dag_run_id in _extract_airflow_refs_from_extra(ex):
            key = (dag_id or "", dag_run_id)
            if key in seen:
                continue
            seen.add(key)
            airflow_refs.append({"dag_id": dag_id or "", "dag_run_id": dag_run_id, "ts_utc": ev.get("ts_utc", "")})

    return _render(
        request,
        "decision_registry.html",
        page_title=f"🗂 Decision: {decision_id}",
        mode="detail",
        decision_id=decision_id,
        events=events,
        latest=latest,
        latest_intent=intent,
        latest_extra=extra_latest,
        airflow_refs=airflow_refs,
    )
