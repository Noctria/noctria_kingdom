# noctria_gui/routes/pdca_api.py
# -*- coding: utf-8 -*-
"""
PDCA API Router — summary/details/entry + exports
- GET /pdca/api/summary
- GET /pdca/api/details
- GET /pdca/api/entry
- GET /pdca/api/export.csv
- GET /pdca/api/export.json

要件:
- summary: totals, by_day[], details[]（オプション）を返す
- details: summaryと同じ構造の配列を返す（負荷対策で分離可能）
- entry : id優先 or (date+tag) で1件
- win_rate/max_drawdown は 0-1 の小数で返す
- X-Request-Id を全レスポンスに付与
- 404/500 エラーハンドリング
- 依存サービス未整備でもダミーデータで動作
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

# 依存サービス（あれば利用、無ければダミーへフォールバック）
try:
    from src.plan_data.pdca_summary_service import (
        get_summary,
        get_details,
        get_entry_by_id,
        get_entry_by_date_tag,
        ExportFormat,
        ExportError,
    )
    _HAS_SERVICE = True
except Exception:
    _HAS_SERVICE = False

    # ---- フォールバック実装（最小限） ----
    # ダミーデータを返す純Python版。テーブルスキーマは本番と同一に合わせる。
    from random import Random
    from datetime import timedelta

    class ExportError(RuntimeError):
        pass

    class ExportFormat:
        CSV = "csv"
        JSON = "json"

    def _seeded_rng(tag: Optional[str]) -> Random:
        return Random((tag or "all") + "-pdca-demo")

    def _emit_row(day: datetime, idx: int, tag: str, rng: Random) -> Dict[str, Any]:
        win = max(0.0, min(1.0, rng.uniform(0.35, 0.75)))
        dd = max(0.0, min(1.0, rng.uniform(0.05, 0.25)))
        trades = rng.randint(3, 40)
        adopted = rng.choice([True, False, False])
        return {
            "id": f"demo-{day.strftime('%Y%m%d')}-{tag}-{idx}",
            "decision_id": f"dec-{rng.randint(10000, 99999)}",
            "run_id": f"run-{rng.randint(10000, 99999)}",
            "date": day.strftime("%Y-%m-%d"),
            "tag": tag,
            "win_rate": round(win, 4),
            "max_drawdown": round(dd, 4),
            "rechecks": rng.randint(0, 3),
            "trades": trades,
            "evals": {"rmse": round(rng.uniform(0.1, 0.6), 4), "mae": round(rng.uniform(0.05, 0.4), 4)},
            "adopted": adopted,
        }

    def _gen_range(date_from: Optional[str], date_to: Optional[str]):
        end = datetime.strptime(date_to, "%Y-%m-%d") if date_to else datetime.utcnow()
        start = datetime.strptime(date_from, "%Y-%m-%d") if date_from else (end - timedelta(days=14))
        cur = start
        while cur <= end:
            yield cur
            cur += timedelta(days=1)

    def get_details(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        tag = filters.get("tag") or "veritas-demo"
        rng = _seeded_rng(tag)
        arr: List[Dict[str, Any]] = []
        for d in _gen_range(filters.get("date_from"), filters.get("date_to")):
            # 日毎に 20~60 行
            for i in range(rng.randint(20, 60)):
                row = _emit_row(d, i, tag, rng)
                # フィルタ適用
                if filters.get("win_diff") is not None:
                    # 便宜上、win_diffは 0〜1 小数差分の閾値として扱う
                    if row["win_rate"] < filters["win_diff"]:
                        continue
                if filters.get("dd_diff") is not None:
                    if row["max_drawdown"] > filters["dd_diff"]:
                        continue
                if filters.get("min_trades") is not None:
                    if row["trades"] < int(filters["min_trades"]):
                        continue
                arr.append(row)
        # ソート
        sort = (filters.get("sort") or "").lower()
        if sort == "win_rate":
            arr.sort(key=lambda r: r["win_rate"], reverse=True)
        elif sort in ("max_drawdown", "maxdd"):
            arr.sort(key=lambda r: r["max_drawdown"])
        elif sort == "trades":
            arr.sort(key=lambda r: r["trades"], reverse=True)
        else:
            arr.sort(key=lambda r: (r["date"], r["tag"], r["id"]))
        # limit/offset
        off = int(filters.get("offset") or 0)
        lim = int(filters.get("limit") or len(arr))
        return arr[off: off + lim]

    def get_summary(filters: Dict[str, Any]) -> Dict[str, Any]:
        det = get_details({**filters, "limit": filters.get("limit") or 5000})  # summary用に十分多め
        by_day: Dict[str, Dict[str, Any]] = {}
        totals = {
            "rows": 0,
            "trades": 0,
            "adopted": 0,
            "avg_win_rate": 0.0,
            "avg_max_drawdown": 0.0,
        }
        wr_sum = 0.0
        dd_sum = 0.0
        for r in det:
            d = r["date"]
            by_day.setdefault(d, {"date": d, "rows": 0, "trades": 0, "avg_win_rate": 0.0, "avg_max_drawdown": 0.0})
            bd = by_day[d]
            bd["rows"] += 1
            bd["trades"] += r["trades"]
            bd["avg_win_rate"] += r["win_rate"]
            bd["avg_max_drawdown"] += r["max_drawdown"]
            totals["rows"] += 1
            totals["trades"] += r["trades"]
            totals["adopted"] += 1 if r["adopted"] else 0
            wr_sum += r["win_rate"]
            dd_sum += r["max_drawdown"]

        # 平均化
        for d, bd in by_day.items():
            if bd["rows"] > 0:
                bd["avg_win_rate"] = round(bd["avg_win_rate"] / bd["rows"], 4)
                bd["avg_max_drawdown"] = round(bd["avg_max_drawdown"] / bd["rows"], 4)
        by_day_list = sorted(by_day.values(), key=lambda x: x["date"])
        if totals["rows"] > 0:
            totals["avg_win_rate"] = round(wr_sum / totals["rows"], 4)
            totals["avg_max_drawdown"] = round(dd_sum / totals["rows"], 4)

        # details を返すかは負荷と方針次第（ここでは返す）
        return {"totals": totals, "by_day": by_day_list, "details": det}

    def get_entry_by_id(entry_id: str) -> Optional[Dict[str, Any]]:
        # ダミーでは全体から線形検索
        det = get_details({"date_from": None, "date_to": None})
        for r in det:
            if r["id"] == entry_id:
                return r
        return None

    def get_entry_by_date_tag(date: str, tag: str) -> Optional[Dict[str, Any]]:
        det = get_details({"date_from": date, "date_to": date, "tag": tag})
        return det[0] if det else None
    # ---- フォールバック終わり ----


router = APIRouter(prefix="/pdca/api", tags=["pdca"])

# ---- モデル定義（返却整形の型保証に使用） ----
class TotalsModel(BaseModel):
    rows: int
    trades: int
    adopted: int
    avg_win_rate: float
    avg_max_drawdown: float

class ByDayModel(BaseModel):
    date: str
    rows: int
    trades: int
    avg_win_rate: float
    avg_max_drawdown: float

class DetailModel(BaseModel):
    id: str
    decision_id: str
    run_id: str
    date: str
    tag: str
    win_rate: float = Field(ge=0.0, le=1.0)
    max_drawdown: float = Field(ge=0.0, le=1.0)
    rechecks: int
    trades: int
    evals: Dict[str, Any]
    adopted: bool

class SummaryResponse(BaseModel):
    totals: TotalsModel
    by_day: List[ByDayModel]
    details: Optional[List[DetailModel]] = None


def _with_request_id(payload: Any, status_code: int = 200) -> JSONResponse:
    req_id = str(uuid4())
    resp = JSONResponse(content=payload, status_code=status_code)
    resp.headers["X-Request-Id"] = req_id
    return resp


@router.get("/summary", response_model=SummaryResponse)
def api_summary(
    request: Request,
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str]   = Query(None, description="YYYY-MM-DD"),
    tag: Optional[str]       = Query(None),
    win_diff: Optional[float]= Query(None, ge=0.0, le=1.0, description="勝率差分しきい値（0-1）"),
    dd_diff: Optional[float] = Query(None, ge=0.0, le=1.0, description="最大DDしきい値（0-1, 以下）"),
    min_trades: Optional[int]= Query(None, ge=0),
    sort: Optional[str]      = Query(None, description="win_rate|max_drawdown|maxdd|trades|date"),
    limit: Optional[int]     = Query(None, ge=1, le=10000),
    offset: Optional[int]    = Query(0, ge=0),
    with_details: Optional[bool] = Query(True),
):
    try:
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "tag": tag,
            "win_diff": win_diff,
            "dd_diff": dd_diff,
            "min_trades": min_trades,
            "sort": sort,
            "limit": limit,
            "offset": offset,
        }
        summary = get_summary(filters)
        # details を含めない指定
        if not with_details and "details" in summary:
            summary = {**summary, "details": None}
        return _with_request_id(summary)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"summary failed: {type(e).__name__}: {e}") from e


@router.get("/details", response_model=List[DetailModel])
def api_details(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str]   = Query(None),
    tag: Optional[str]       = Query(None),
    win_diff: Optional[float]= Query(None, ge=0.0, le=1.0),
    dd_diff: Optional[float] = Query(None, ge=0.0, le=1.0),
    min_trades: Optional[int]= Query(None, ge=0),
    sort: Optional[str]      = Query(None),
    limit: Optional[int]     = Query(2000, ge=1, le=20000),
    offset: Optional[int]    = Query(0, ge=0),
):
    try:
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "tag": tag,
            "win_diff": win_diff,
            "dd_diff": dd_diff,
            "min_trades": min_trades,
            "sort": sort,
            "limit": limit,
            "offset": offset,
        }
        rows = get_details(filters)
        return _with_request_id(rows)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"details failed: {type(e).__name__}: {e}") from e


@router.get("/entry")
def api_entry(
    request: Request,
    id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
):
    try:
        row = None
        if id:
            row = get_entry_by_id(id)
        else:
            if not date or not tag:
                raise HTTPException(400, "date and tag are required when id is not provided")
            row = get_entry_by_date_tag(date, tag)
        if not row:
            raise HTTPException(404, "not found")
        return _with_request_id(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"entry failed: {type(e).__name__}: {e}") from e


@router.get("/export.csv", response_class=PlainTextResponse)
def api_export_csv(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str]   = Query(None),
    tag: Optional[str]       = Query(None),
):
    try:
        # まず details を取得してCSVにする（サービス側でCSV生成できるなら差し替え）
        rows = get_details({"date_from": date_from, "date_to": date_to, "tag": tag, "limit": 100000})
        if not rows:
            return _with_request_id("", status_code=200)
        # 手軽なCSV化
        cols = ["id","decision_id","run_id","date","tag","win_rate","max_drawdown","rechecks","trades","adopted"]
        lines = [",".join(cols)]
        for r in rows:
            line = ",".join(str(r.get(c, "")) for c in cols)
            lines.append(line)
        resp = PlainTextResponse("\n".join(lines))
        resp.headers["X-Request-Id"] = str(uuid4())
        resp.headers["Content-Disposition"] = 'attachment; filename="pdca_export.csv"'
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"export csv failed: {type(e).__name__}: {e}") from e


@router.get("/export.json")
def api_export_json(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str]   = Query(None),
    tag: Optional[str]       = Query(None),
):
    try:
        rows = get_details({"date_from": date_from, "date_to": date_to, "tag": tag, "limit": 100000})
        return _with_request_id(rows)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"export json failed: {type(e).__name__}: {e}") from e
