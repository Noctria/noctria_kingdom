# src/plan_data/pdca_summary_service.py
# -*- coding: utf-8 -*-
"""
PDCAサマリー用のデータ取得＆KPI集計ユーティリティ

優先ソース: Postgres テーブル `obs_infer_calls`
  必須カラム: started_at, ended_at, ai_name, status, params_json, metrics_json

役割:
  1) 期間指定で obs_infer_calls を取得（接続不可や未作成時は安全に空配列）
  2) KPI（評価件数/再評価件数/採用件数/採用率/平均勝率/最大DD/取引数）を集計
  3) 日次集計（勝率・件数・取引数）を生成

環境変数:
  - NOCTRIA_OBS_PG_DSN （推奨）
    例: postgresql://user:pass@host:5432/dbname
  - もしくは POSTGRES_HOST/PORT/DB/USER/PASSWORD からDSNを組み立て

返却値の単位:
  - win_rate: 0〜1 の比率（UI側で%表記に変換してください）
  - max_drawdown: 0〜1 の比率（負の値を返せる実装でも可。ここではそのまま）
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---- DB 接続（psycopg v3 → v2 フォールバック） ----
try:
    import psycopg  # type: ignore
except Exception:
    psycopg = None  # type: ignore

try:
    import psycopg2  # type: ignore
except Exception:
    psycopg2 = None  # type: ignore


# ---------------------------------------------------------------------
# DSN/接続
# ---------------------------------------------------------------------
def _get_dsn() -> Optional[str]:
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if dsn:
        return dsn

    # 後方互換: 個別ENVから組み立て
    host = os.getenv("POSTGRES_HOST", "localhost")
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

    q = """
        SELECT started_at, ended_at, ai_name, status, params_json, metrics_json
          FROM obs_infer_calls
         WHERE started_at >= %s AND started_at <= %s
         ORDER BY started_at ASC
    """
    start_utc = _to_utc_start(from_date)
    end_utc = _to_utc_end(to_date)

    rows: List[InferRow] = []
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(q, (start_utc, end_utc))
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

                    rows.append(
                        InferRow(
                            started_at=started_at,
                            ended_at=ended_at,
                            ai_name=ai_name,
                            status=status,
                            params_json=params,
                            metrics_json=metrics,
                        )
                    )
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
    act = str(row.params_json.get("action", "")).lower()
    phase = str(row.params_json.get("phase", "")).lower()
    return act in ("evaluate", "re-evaluate", "recheck", "eval") or phase in ("evaluate", "recheck", "eval")


def _is_recheck(row: InferRow) -> bool:
    name = row.ai_name.lower()
    if "recheck" in name:
        return True
    if str(row.params_json.get("recheck", "")).lower() in ("1", "true", "yes", "on"):
        return True
    reason = str(row.params_json.get("reason", "")).lower()
    return "recheck" in reason


def _is_adopt(row: InferRow) -> bool:
    name = row.ai_name.lower()
    if "adopt" in name or "act" in name or "push" in name:
        return True
    act = str(row.params_json.get("action", "")).lower()
    return act in ("adopt", "push", "act")


def _get_num(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in d and isinstance(d[k], (int, float)):
            try:
                return float(d[k])
            except Exception:
                continue
    return None


def _get_int(d: Dict[str, Any], *keys: str) -> Optional[int]:
    for k in keys:
        if k in d and isinstance(d[k], int):
            return int(d[k])
        if k in d and isinstance(d[k], float):
            try:
                return int(d[k])
            except Exception:
                continue
    return None


# ---------------------------------------------------------------------
# 集計
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
        wr = _get_num(m, "win_rate", "success_ratio", "accuracy")
        if wr is not None and 0.0 <= wr <= 1.0:
            win_rates.append(wr)
        else:
            wins = _get_int(m, "wins", "n_wins", "successful_trades")
            total = _get_int(m, "trades", "num_trades", "n_trades", "total_trades", "episodes")
            if wins is not None and total and total > 0:
                wins_sum += wins
                trades_sum_for_win += total

        # --- 最大DD（より小さいほど悪い想定。ここではそのまま最小値を代表値に）---
        dd = _get_num(m, "max_drawdown", "max_dd", "mdd")
        if dd is not None:
            dd_values.append(dd)

        # --- 取引数 ---
        t = _get_int(m, "trades", "num_trades", "n_trades", "total_trades")
        if t is not None:
            trades_sum += t

    # 集計勝率
    agg_win_rate: Optional[float] = None
    if win_rates:
        agg_win_rate = sum(win_rates) / len(win_rates)
    elif trades_sum_for_win > 0:
        agg_win_rate = wins_sum / trades_sum_for_win

    # 最大DD: 最悪値（最小値）を採用
    agg_max_dd: Optional[float] = min(dd_values) if dd_values else None

    adopt_rate = (total_adopted / total_evals) if total_evals > 0 else None

    # 後方互換: adopt_rate を正式キーに、adoption_rate も併記
    return {
        "evals": total_evals,
        "rechecks": total_rechecks,
        "adopted": total_adopted,
        "adopt_rate": adopt_rate,        # 正式
        "adoption_rate": adopt_rate,     # 互換（フロント実装差異に配慮）
        "win_rate": agg_win_rate,        # 0-1 or None
        "max_drawdown": agg_max_dd,      # 例: -0.12（-12%）/ 0.12（12%）
        "trades": trades_sum,
    }


def aggregate_by_day(rows: List[InferRow]) -> List[Dict[str, Any]]:
    """
    日次でまとめてグラフ用の配列を返す。
      - date: YYYY-MM-DD（UTC日付）
      - evals, adopted, trades, win_rate(平均または wins/total 推定)
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

        t = _get_int(r.metrics_json, "trades", "num_trades", "n_trades", "total_trades") or 0
        b["trades"] += t

        wr = _get_num(r.metrics_json, "win_rate", "success_ratio", "accuracy")
        if wr is not None and 0 <= wr <= 1.0:
            b["_win_rates"].append(wr)
        else:
            wins = _get_int(r.metrics_json, "wins", "n_wins", "successful_trades")
            total = _get_int(r.metrics_json, "trades", "num_trades", "n_trades", "total_trades", "episodes")
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

        out.append(
            {
                "date": b["date"],
                "evals": b["evals"],
                "adopted": b["adopted"],
                "trades": b["trades"],
                "win_rate": wr,  # 0-1 or None
            }
        )

    return out
