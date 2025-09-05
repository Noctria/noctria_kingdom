# noctria_gui/routes/pdca_api_details.py など新規 or 既存置換

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Tuple
from datetime import date

router = APIRouter()

# フロントが使うソートキーを固定して安全化
SortKey = Literal["date", "tag", "evals", "adopted", "win_rate", "max_drawdown", "rechecks", "trades"]
SortDir = Literal["asc", "desc"]

class DetailRow(BaseModel):
    date: str
    tag: str
    evals: int = 0
    adopted: int = 0
    win_rate: Optional[float] = None      # 0.0-1.0（API内では比率、フロントで%化）
    max_drawdown: Optional[float] = None  # 0.0-1.0 の負方向
    rechecks: int = 0
    trades: int = 0

class DetailsResponse(BaseModel):
    items: List[DetailRow]
    total: int = Field(..., description="フィルター後の総件数")
    limit: int
    offset: int
    sort_key: SortKey
    sort_dir: SortDir

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s: return None
    return date.fromisoformat(s)

def _build_filters(
    date_from: Optional[str],
    date_to: Optional[str],
    tag: Optional[str],
    win_diff: Optional[float],
    dd_diff: Optional[float],
    min_trades: Optional[int],
) -> dict:
    # ここで ORM/SQL 条件を構築（例：SQLAlchemy の filter 条件）
    # 以降は疑似コード。実プロジェクトのモデルや集計テーブルに合わせて適宜差し替え。
    return {
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "tag": (tag or "").strip() or None,
        "win_diff": win_diff,       # 例：ベンチとの差分(%)をAPIが受けるならここで変換
        "dd_diff": dd_diff,         # 同上
        "min_trades": min_trades or 0,
    }

def _allowed(sort_key: str) -> SortKey:
    allowed = {"date","tag","evals","adopted","win_rate","max_drawdown","rechecks","trades"}
    if sort_key not in allowed:
        return "date"  # 既定
    return sort_key  # type: ignore

@router.get("/pdca/api/details", response_model=DetailsResponse)
def get_details(
    date_from: Optional[str] = Query(None, alias="date_from"),
    date_to: Optional[str] = Query(None, alias="date_to"),
    tag: Optional[str] = None,
    win_diff: Optional[float] = None,
    dd_diff: Optional[float] = None,
    min_trades: Optional[int] = Query(None, ge=0),
    # ページング
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    # ソート
    sort_key: SortKey = Query("date"),
    sort_dir: SortDir = Query("desc"),
):
    """
    クエリ例:
      /pdca/api/details?date_from=2025-08-01&date_to=2025-08-20&tag=veritas&limit=50&offset=0&sort_key=win_rate&sort_dir=desc
    返り値:
      { items:[...], total:1234, limit:50, offset:0, sort_key:"win_rate", sort_dir:"desc" }
    """
    try:
        filters = _build_filters(date_from, date_to, tag, win_diff, dd_diff, min_trades)

        # ===== ここからデータアクセス層 =====
        # 例）SQLAlchemy:
        # q = session.query(AggregatedDailyTag)  # date, tag, evals, adopted, win_rate, max_drawdown, rechecks, trades
        # if filters["date_from"]: q = q.filter(AggregatedDailyTag.date >= filters["date_from"])
        # if filters["date_to"]:   q = q.filter(AggregatedDailyTag.date <= filters["date_to"])
        # if filters["tag"]:       q = q.filter(AggregatedDailyTag.tag.ilike(f"%{filters['tag']}%"))
        # if filters["min_trades"]:q = q.filter(AggregatedDailyTag.trades >= filters["min_trades"])
        # ※ win_diff, dd_diff の扱いはあなたの定義に合わせて（別列 or 計算列）
        #
        # total = q.count()
        # # ソート
        # key_map = {
        #   "date": AggregatedDailyTag.date,
        #   "tag": AggregatedDailyTag.tag,
        #   "evals": AggregatedDailyTag.evals,
        #   "adopted": AggregatedDailyTag.adopted,
        #   "win_rate": AggregatedDailyTag.win_rate,
        #   "max_drawdown": AggregatedDailyTag.max_drawdown,
        #   "rechecks": AggregatedDailyTag.rechecks,
        #   "trades": AggregatedDailyTag.trades,
        # }
        # col = key_map[_allowed(sort_key)]
        # q = q.order_by(col.asc() if sort_dir=="asc" else col.desc())
        # rows = q.offset(offset).limit(limit).all()

        # DEMO: ダミーデータ（実装時は↑のDBアクセスに置換）
        import random
        import datetime as dt
        rng = random.Random(42)
        DF = _parse_date(date_from) or dt.date.today().replace(day=1)
        DT = _parse_date(date_to) or dt.date.today()
        days = (DT - DF).days + 1
        universe = []
        for i in range(max(1, days)):
            d = DF + dt.timedelta(days=i)
            for tg in (["veritas","levia","sirius"] if not tag else [tag]):
                r = {
                    "date": d.isoformat(),
                    "tag": tg,
                    "evals": rng.randint(0, 30),
                    "adopted": rng.randint(0, 10),
                    "win_rate": rng.random(),             # 0-1
                    "max_drawdown": -rng.random()*0.2,    # 0 ～ -0.2
                    "rechecks": rng.randint(0, 5),
                    "trades": rng.randint(10, 120),
                }
                if r["trades"] >= (filters["min_trades"] or 0):
                    universe.append(r)

        total = len(universe)
        # ソート
        sk = _allowed(sort_key)
        reverse = (sort_dir == "desc")
        def _key(r):
            v = r.get(sk)
            # None 安定化（末尾送り）
            return (v is None, v)
        universe.sort(key=_key, reverse=reverse)
        # ページング
        page = universe[offset: offset+limit]

        return DetailsResponse(
            items=[DetailRow(**it) for it in page],
            total=total,
            limit=limit,
            offset=offset,
            sort_key=sk, sort_dir=sort_dir
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
