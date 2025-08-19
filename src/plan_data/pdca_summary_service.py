# src/plan_data/pdca_summary_service.py
# -*- coding: utf-8 -*-
"""
PDCAサマリー用のデータ取得＆KPI集計ユーティリティ

優先ソース: Postgres テーブル/ビュー `obs_infer_calls`
  想定カラム:
    - started_at (timestamp/timestamptz)
    - ended_at   (timestamp/timestamptz, nullable)
    - ai_name    (text)
    - status     (text) 例: 'success' / 'failed' / ...
    - params_json  (json/jsonb) 例: {tag, decision_id, run_id, action, ...}
    - metrics_json (json/jsonb) 例: {win_rate, max_drawdown, trades, ...}
    - （任意）id (uuid/text) — 無ければ派生IDを生成して返す

役割:
  1) 期間指定で obs_infer_calls を取得（接続不可や未作成時は安全に空配列）
  2) KPI（評価件数/再評価件数/採用件数/採用率/平均勝率/最大DD/取引数）を集計
  3) 日次集計（勝率・件数・取引数）を生成
  4) フロント期待形式の details/summary/entry API用データを返却

環境変数:
  - NOCTRIA_OBS_PG_DSN （推奨）
    例: postgresql://user:pass@host:5432/dbname
  - もしくは POSTGRES_HOST/PORT/DB/USER/PASSWORD からDSNを組み立て

返却値の単位:
  - win_rate: 0〜1 の比率（UI側で%表記に変換）
  - max_drawdown: 0〜1 の比率（負値の実装でもそのまま返す）
"""

from __future__ import annotations

import os
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Iterable

# ---- DB 接続（psycopg v3 → v2 フォールバック）----
try:
    import psycopg  # type: ignore
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore


# ---------------------------------------------------------------------
# DSN/接続
# ---------------------------------------------------------------------
def _get_dsn() -> Optional[str]:
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if dsn:
        return dsn

    # 後方互換: 個別ENVから組み立て（既定は 127.0.0.1:5432 に統一）
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "noctria_db")
    user = os.getenv("POSTGRES_USER", "noctria")
    pw = os.getenv("POSTGRES_PASSWORD", "noctria")
    if host and db and user:
        return f"postgresql://{user}:{pw}@{host}:{port}/{db}"
    return None


def _connect():
    """
    接続オブジェクトを返す。失敗時は None。
    psycopg(3)→psycopg2(2) の順で試行。
    """
    dsn = _get_dsn()
    if not dsn:
        return None

    if psycopg is not None:
        try:
            return psycopg.connect(dsn, autocommit=False)
        except Exception:
            pass

    if psycopg2 is not None:
        try:
            return psycopg2.connect(dsn)
        except Exception:
            pass

    return None


def _to_utc_start(dt_date: datetime) -> datetime:
    """日付(naive/aware問わず)の 00:00:00Z"""
    return datetime(dt_date.year, dt_date.month, dt_date.day, tzinfo=timezone.utc)


def _to_utc_end(dt_date: datetime) -> datetime:
    """日付(naive/aware問わず)の 23:59:59Z"""
    return datetime(dt_date.year, dt_date.month, dt_date.day, 23, 59, 59, tzinfo=timezone.utc)


# ---------------------------------------------------------------------
# 型とユーティリティ
# ---------------------------------------------------------------------
@dataclass
class InferRow:
    started_at: datetime
    ended_at: Optional[datetime]
    ai_name: str
    status: str
    params_json: Dict[str, Any]
    metrics_json: Dict[str, Any]
    raw_id: Optional[str] = None  # テーブルにidがある場合のみ


def _load_json(val: Any) -> Dict[str, Any]:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def _first_str(d: Dict[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            s = str(v)
            return s if s != "" else None
    return None


def _first_num(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)):
            try:
                return float(v)
            except Exception:
                continue
    return None


def _first_int(d: Dict[str, Any], *keys: str) -> Optional[int]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            try:
                return int(v)
            except Exception:
                continue
    return None


def _derived_id(started_at: datetime, ai_name: str, decision_id: Optional[str], run_id: Optional[str]) -> str:
    """
    テーブルに id が無い場合の安定ID（ビューでも同一行なら同じIDになるよう構成）
    """
    base = f"{started_at.astimezone(timezone.utc).isoformat()}|{ai_name}|{decision_id or ''}|{run_id or ''}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()  # 40文字hex


# ---------------------------------------------------------------------
# 取得
# ---------------------------------------------------------------------
def fetch_infer_calls(from_date: datetime, to_date: datetime) -> List[InferRow]:
    """
    obs_infer_calls から from_date〜to_date(含む) の行を取得。
    取得失敗/未接続でも空配列を返す（UI/上位はGracefulに継続可能）。
    """
    conn = _connect()
    if conn is None:
        return []

    # id列の有無に依らず動くよう、SELECT句を2通り試す
    # まず id あり想定のクエリを実行し、失敗したら id なし版へフォールバック
    start_utc = _to_utc_start(from_date)
    end_utc = _to_utc_end(to_date)

    rows: List[InferRow] = []
    q_with_id = """
        SELECT id, started_at, ended_at, ai_name, status, params_json, metrics_json
          FROM obs_infer_calls
         WHERE started_at >= %s AND started_at <= %s
         ORDER BY started_at ASC
    """
    q_no_id = """
        SELECT started_at, ended_at, ai_name, status, params_json, metrics_json
          FROM obs_infer_calls
         WHERE started_at >= %s AND started_at <= %s
         ORDER BY started_at ASC
    """

    try:
        with conn:
            with conn.cursor() as cur:
                # try with id
                try:
                    cur.execute(q_with_id, (start_utc, end_utc))
                    for rec in cur.fetchall():
                        raw_id = str(rec[0]) if rec[0] is not None else None
                        started_at = rec[1]
                        ended_at = rec[2]
                        ai_name = rec[3] or ""
                        status = rec[4] or ""
                        params = _load_json(rec[5])
                        metrics = _load_json(rec[6])
                        if isinstance(started_at, str):
                            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                        if isinstance(ended_at, str):
                            ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                        rows.append(InferRow(started_at, ended_at, ai_name, status, params, metrics, raw_id))
                except Exception:
                    # fallback: no id column
                    cur.execute(q_no_id, (start_utc, end_utc))
                    for rec in cur.fetchall():
                        started_at = rec[0]
                        ended_at = rec[1]
                        ai_name = rec[2] or ""
                        status = rec[3] or ""
                        params = _load_json(rec[4])
                        metrics = _load_json(rec[5])
                        if isinstance(started_at, str):
                            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                        if isinstance(ended_at, str):
                            ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                        rows.append(InferRow(started_at, ended_at, ai_name, status, params, metrics, None))
    except Exception:
        # DBクエリが失敗してもUIを止めない
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return rows


# ---------------------------------------------------------------------
# 判定ヘルパ
# ---------------------------------------------------------------------
def _is_eval(row: InferRow) -> bool:
    name = row.ai_name.lower()
    if "eval" in name or "recheck" in name:
        return True
    act = _first_str(row.params_json, "action", "mode", "phase")
    act = (act or "").lower()
    return act in ("evaluate", "re-evaluate", "recheck", "eval")


def _is_recheck(row: InferRow) -> bool:
    name = row.ai_name.lower()
    if "recheck" in name:
        return True
    if _first_str(row.params_json, "recheck") in ("1", "true", "yes", "on", "True", "TRUE"):
        return True
    reason = (_first_str(row.params_json, "reason") or "").lower()
    return "recheck" in reason


def _is_adopt(row: InferRow) -> bool:
    name = row.ai_name.lower()
    if "adopt" in name or "act" in name or "push" in name:
        return True
    act = (_first_str(row.params_json, "action") or "").lower()
    return act in ("adopt", "push", "act")


# ---------------------------------------------------------------------
# 集計（KPI/日次）
# ---------------------------------------------------------------------
def aggregate_kpis(rows: List[InferRow]) -> Dict[str, Any]:
    """
    柔軟なメトリクス抽出：
      - 勝率: metrics_json.win_rate / success_ratio / accuracy を優先。
              無ければ wins / trades から推定。
      - 最大DD: metrics_json.max_drawdown / max_dd / mdd
      - 取引数: metrics_json.trades / num_trades / n_trades / total_trades
    """
    total_evals = sum(1 for r in rows if _is_eval(r))
    total_rechecks = sum(1 for r in rows if _is_recheck(r))
    total_adopted = sum(1 for r in rows if _is_adopt(r) and r.status.lower() == "success")

    # win-rate 合成用
    win_rates: List[float] = []
    wins_sum = 0
    trades_sum_for_win = 0

    # DD & Trades
    dd_values: List[float] = []
    trades_sum = 0

    for r in rows:
        m = r.metrics_json

        # --- 勝率 ---
        wr = _first_num(m, "win_rate", "success_ratio", "accuracy")
        if wr is not None and -1.0 <= wr <= 1.0:  # （負値実装が来ても0〜1に丸めない：生値を尊重）
            win_rates.append(wr)
        else:
            wins = _first_int(m, "wins", "n_wins", "successful_trades")
            total = _first_int(m, "trades", "num_trades", "n_trades", "total_trades", "episodes")
            if wins is not None and total and total > 0:
                wins_sum += wins
                trades_sum_for_win += total

        # --- 最大DD ---
        dd = _first_num(m, "max_drawdown", "max_dd", "mdd")
        if dd is not None:
            dd_values.append(dd)

        # --- 取引数 ---
        t = _first_int(m, "trades", "num_trades", "n_trades", "total_trades")
        if t is not None:
            trades_sum += t

    # 集計勝率
    agg_win_rate: Optional[float] = None
    if win_rates:
        agg_win_rate = sum(win_rates) / len(win_rates)
    elif trades_sum_for_win > 0:
        agg_win_rate = wins_sum / trades_sum_for_win

    # 最大DD: 「より小さいほど悪い」という前提の最悪値を代表（最小値）
    agg_max_dd: Optional[float] = min(dd_values) if dd_values else None

    # 採用率: 分母ゼロ(評価=0)でも採用データだけある場合にフォールバック
    effective_total = total_evals if total_evals > 0 else (total_evals + total_adopted)
    adopt_rate = (total_adopted / effective_total) if effective_total > 0 else None

    return {
        "evals": total_evals,
        "rechecks": total_rechecks,
        "adopted": total_adopted,
        "adopt_rate": adopt_rate,        # 0-1 or None
        "adoption_rate": adopt_rate,     # 互換
        "win_rate": agg_win_rate,        # 0-1 or None / （負値実装ならそのまま）
        "max_drawdown": agg_max_dd,      # 例: -0.12 / 0.12
        "trades": trades_sum,
    }


def aggregate_by_day(rows: List[InferRow]) -> List[Dict[str, Any]]:
    """
    日次でまとめてグラフ用の配列を返す。
      - date: YYYY-MM-DD（UTC日付）
      - evals, adopted, trades, win_rate(平均または wins/total 推定), adopt_rate(フォールバック含む)
    """
    from collections import defaultdict

    buckets: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "date": "",
            "evals": 0,
            "adopted": 0,
            "trades": 0,
            "_win_rates": [],
            "_wins": 0,
            "_total": 0,
        }
    )

    def _key(dt_: datetime) -> str:
        d = dt_.astimezone(timezone.utc).date()
        return d.isoformat()

    for r in rows:
        key = _key(r.started_at)
        b = buckets[key]
        b["date"] = key

        if _is_eval(r):
            b["evals"] += 1
        if _is_adopt(r) and r.status.lower() == "success":
            b["adopted"] += 1

        t = _first_int(r.metrics_json, "trades", "num_trades", "n_trades", "total_trades") or 0
        b["trades"] += t

        wr = _first_num(r.metrics_json, "win_rate", "success_ratio", "accuracy")
        if wr is not None and -1.0 <= wr <= 1.0:
            b["_win_rates"].append(wr)
        else:
            wins = _first_int(r.metrics_json, "wins", "n_wins", "successful_trades")
            total = _first_int(r.metrics_json, "trades", "num_trades", "n_trades", "total_trades", "episodes")
            if wins is not None and total:
                b["_wins"] += wins
                b["_total"] += total

    out: List[Dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        # 日次勝率: 平均 or wins/total
        wr: Optional[float] = None
        if b["_win_rates"]:
            wr = sum(b["_win_rates"]) / len(b["_win_rates"])
        elif b["_total"] > 0:
            wr = b["_wins"] / b["_total"]

        # 日次採用率: 分母ゼロ(評価=0)なら evals+adopted でフォールバック
        effective_total = b["evals"] if b["evals"] > 0 else (b["evals"] + b["adopted"])
        adopt_rate = (b["adopted"] / effective_total) if effective_total > 0 else None

        out.append(
            {
                "date": b["date"],
                "evals": b["evals"],
                "adopted": b["adopted"],
                "trades": b["trades"],
                "win_rate": wr,       # 0-1 or None / （負値実装でもそのまま）
                "adopt_rate": adopt_rate,  # 0-1 or None
            }
        )

    return out


# ---------------------------------------------------------------------
# フロント期待形式の生成（details / summary / entry）
# ---------------------------------------------------------------------
def _rows_to_details(rows: Iterable[InferRow]) -> List[Dict[str, Any]]:
    """
    InferRow -> details[] (フロント期待形)
      必須キー:
        id, decision_id, run_id, date(YYYY-MM-DD), tag, win_rate, max_drawdown, rechecks, trades, evals(dict), adopted(bool)
    """
    out: List[Dict[str, Any]] = []
    for r in rows:
        p = r.params_json
        m = r.metrics_json

        decision_id = _first_str(p, "decision_id", "decisionId", "decision", "dec_id")
        run_id = _first_str(p, "run_id", "runId", "run", "airflow_run_id", "execution_id")
        tag = _first_str(p, "tag", "strategy_tag", "strategyTag", "label") or r.ai_name

        # KPI
        win_rate = _first_num(m, "win_rate", "success_ratio", "accuracy")
        if win_rate is None:
            wins = _first_int(m, "wins", "n_wins", "successful_trades")
            total = _first_int(m, "trades", "num_trades", "n_trades", "total_trades", "episodes")
            win_rate = (wins / total) if (wins is not None and total and total > 0) else None

        max_dd = _first_num(m, "max_drawdown", "max_dd", "mdd")
        trades = _first_int(m, "trades", "num_trades", "n_trades", "total_trades") or 0

        # 再評価フラグ（行単位）
        recheck_flag = 1 if _is_recheck(r) else 0

        # 採用フラグ
        adopted = bool(_is_adopt(r) and r.status.lower() == "success")

        # id
        _id = r.raw_id or _derived_id(r.started_at, r.ai_name, decision_id, run_id)

        out.append(
            {
                "id": _id,
                "decision_id": decision_id or "",
                "run_id": run_id or "",
                "date": r.started_at.astimezone(timezone.utc).date().isoformat(),
                "tag": tag,
                "win_rate": float(win_rate) if win_rate is not None else None,
                "max_drawdown": float(max_dd) if max_dd is not None else None,
                "rechecks": recheck_flag,
                "trades": int(trades),
                "evals": m if isinstance(m, dict) else {},
                "adopted": adopted,
            }
        )
    return out


def get_details(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    フィルタを適用した details[] を返す。
      受け取る可能性のあるキー:
        - date_from, date_to (YYYY-MM-DD)
        - tag
        - win_diff (float, 下限) / dd_diff (float, 上限) / min_trades (int, 下限)
        - sort (win_rate|max_drawdown|maxdd|trades|date)
        - limit, offset
    """
    # 期間解決（未指定は「直近14日」）
    end = datetime.utcnow().date()
    start = end - timedelta(days=14)
    if filters.get("date_from"):
        start = datetime.strptime(filters["date_from"], "%Y-%m-%d").date()
    if filters.get("date_to"):
        end = datetime.strptime(filters["date_to"], "%Y-%m-%d").date()

    rows = fetch_infer_calls(datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.min.time()))
    det = _rows_to_details(rows)

    # フィルタ
    tag = filters.get("tag")
    if tag:
        det = [r for r in det if r["tag"] == tag]

    win_diff = filters.get("win_diff")
    if win_diff is not None:
        try:
            thr = float(win_diff)
            det = [r for r in det if r["win_rate"] is not None and r["win_rate"] >= thr]
        except Exception:
            pass

    dd_diff = filters.get("dd_diff")
    if dd_diff is not None:
        try:
            thr = float(dd_diff)
            det = [r for r in det if r["max_drawdown"] is not None and r["max_drawdown"] <= thr]
        except Exception:
            pass

    min_trades = filters.get("min_trades")
    if min_trades is not None:
        try:
            thr = int(min_trades)
            det = [r for r in det if r["trades"] >= thr]
        except Exception:
            pass

    # ソート
    sort = (filters.get("sort") or "").lower()
    if sort == "win_rate":
        det.sort(key=lambda r: (r["win_rate"] is None, r["win_rate"]), reverse=True)
    elif sort in ("max_drawdown", "maxdd"):
        det = [r for r in det if r["max_drawdown"] is not None] + [r for r in det if r["max_drawdown"] is None]
        det.sort(key=lambda r: (r["max_drawdown"] is None, r["max_drawdown"]))  # 小さい方が先
    elif sort == "trades":
        det.sort(key=lambda r: r["trades"], reverse=True)
    else:  # date/tag/id
        det.sort(key=lambda r: (r["date"], r["tag"], r["id"]))

    # limit/offset
    off = int(filters.get("offset") or 0)
    lim = int(filters.get("limit") or len(det))
    return det[off: off + lim]


def get_summary(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    summary: { totals, by_day[], details[] }
      - totals: { rows, trades, adopted, avg_win_rate, avg_max_drawdown }
      - by_day: [{ date, rows, trades, avg_win_rate, avg_max_drawdown }]
      - details: 上記 get_details() と同型（必要に応じてAPI側で非含有にできる）
    """
    det = get_details({**filters, "limit": filters.get("limit") or 100000})
    # totals/by_day を再計算
    rows_for_agg: List[InferRow] = []
    # detailsからInferRowへ戻す必要は本来ないが、既存集計関数を活用するため最小限リフレーム
    for d in det:
        started = datetime.fromisoformat(d["date"])  # naive (UTC日付だけ持つ)
        started = datetime(started.year, started.month, started.day, tzinfo=timezone.utc)
        rows_for_agg.append(
            InferRow(
                started_at=started,
                ended_at=None,
                ai_name=d.get("tag", ""),
                status=("success" if d.get("adopted") else "unknown"),
                params_json={"action": "evaluate", "tag": d.get("tag", "")},
                metrics_json={
                    "win_rate": d.get("win_rate"),
                    "max_drawdown": d.get("max_drawdown"),
                    "trades": d.get("trades"),
                },
            )
        )

    # totals
    k = aggregate_kpis(rows_for_agg)
    totals = {
        "rows": len(det),
        "trades": int(k.get("trades") or 0),
        "adopted": int(k.get("adopted") or 0),
        "avg_win_rate": float(k.get("win_rate")) if k.get("win_rate") is not None else None,
        "avg_max_drawdown": float(k.get("max_drawdown")) if k.get("max_drawdown") is not None else None,
    }

    # by_day
    byday_raw = aggregate_by_day(rows_for_agg)
    # aggregate_by_day は evals/adopted/trades/win_rate/adopt_rate を返すので、
    # 期待形に正規化（rows=evals相当）
    by_day = []
    for b in byday_raw:
        rows_cnt = int(b.get("evals") or 0)
        wr = b.get("win_rate")
        dd = None  # 詳細粒度が無いのでby_dayのDD平均は省略（必要なら別集約を追加）
        by_day.append(
            {
                "date": b["date"],
                "rows": rows_cnt,
                "trades": int(b.get("trades") or 0),
                "avg_win_rate": float(wr) if wr is not None else None,
                "avg_max_drawdown": dd,
            }
        )

    return {"totals": totals, "by_day": by_day, "details": det}


def get_entry_by_id(entry_id: str) -> Optional[Dict[str, Any]]:
    """
    id優先で1件返す。テーブルにid列が無い場合は期間を広めにして探索。
    """
    # まず直接クエリを試す（id列がある場合）
    conn = _connect()
    if conn is not None:
        q = """
            SELECT id, started_at, ended_at, ai_name, status, params_json, metrics_json
              FROM obs_infer_calls
             WHERE id = %s
             LIMIT 1
        """
        try:
            with conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute(q, (entry_id,))
                        rec = cur.fetchone()
                        if rec:
                            raw_id = str(rec[0]) if rec[0] is not None else None
                            started_at = rec[1]
                            ended_at = rec[2]
                            ai_name = rec[3] or ""
                            status = rec[4] or ""
                            params = _load_json(rec[5])
                            metrics = _load_json(rec[6])
                            if isinstance(started_at, str):
                                started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                            if isinstance(ended_at, str):
                                ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                            row = InferRow(started_at, ended_at, ai_name, status, params, metrics, raw_id)
                            return _rows_to_details([row])[0]
                    except Exception:
                        # id列が無い／エラー → フォールバック（期間探索）
                        pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # フォールバック：過去90日を探索（コストを抑えるなら14〜30日に調整）
    end = datetime.utcnow().date()
    start = end - timedelta(days=90)
    det = get_details({"date_from": start.isoformat(), "date_to": end.isoformat()})
    for r in det:
        if r["id"] == entry_id:
            return r
    return None


def get_entry_by_date_tag(date: str, tag: str) -> Optional[Dict[str, Any]]:
    """
    (date, tag) で最初の1件を返す
    """
    det = get_details({"date_from": date, "date_to": date, "tag": tag, "limit": 1})
    return det[0] if det else None


# ---------------------------------------------------------------------
# ヘルス/初期化
# ---------------------------------------------------------------------
def healthcheck() -> Tuple[bool, str]:
    """
    DB 接続の生死確認（/healthz から呼ばれる想定）
    成功: (True, 'db=... user=... now=...')
    失敗: (False, 'connect failed: ...')
    """
    conn = _connect()
    if conn is None:
        return False, "connect failed: no driver or DSN unavailable"

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("select current_database(), current_user, now()")
                db, usr, now = cur.fetchone()
        return True, f"db={db} user={usr} now={now}"
    except Exception as e:
        return False, f"connect failed: {type(e).__name__}: {e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def ensure_tables(verbose: bool = False) -> None:
    """
    起動時に呼ばれる想定のダミー実装。
    テーブル作成は本職責務外のため、存在確認だけ行い副作用は与えない。
    """
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('obs_infer_calls')")
                _ = cur.fetchone()
        if verbose:
            print("[pdca_summary_service] ensure_tables: checked (no-op)")
    except Exception:
        # 失敗しても GUI を止めない
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
