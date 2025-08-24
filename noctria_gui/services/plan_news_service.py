# =====================================================================
# Noctria Kingdom — Plan News Service
# 用途:
#   - DBビュー (vw_news_daily_counts / vw_news_event_tags) を読み出し、
#     Chart.js に渡しやすい JSON 形式に整形する“取得ロジック”層。
#   - ルート/テンプレとは分離して、責務を明確化（既存設計に合わせた分担）。
#
# ポイント:
#   - DSNは NOCTRIA_OBS_PG_DSN を優先。未設定時はローカル既定DSNを使用。
#   - fetch_news_timeline(): 日次件数/感情のタイムラインを返す。
#   - fetch_event_impact(): イベント発生日をアンカーに、相対ウィンドウ(-3..+3)で平均集計。
# =====================================================================

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras


def _get_dsn() -> str:
    return os.getenv(
        "NOCTRIA_OBS_PG_DSN",
        "postgresql://noctria:noctria@localhost:5432/noctria_db",
    )


def fetch_news_timeline(
    asset: str = "USDJPY",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    vw_news_daily_counts から、期間・アセットでタイムラインを取得。
    Chart.js にそのまま渡せる形で返す。
    """
    sql = """
    SELECT date, cnt_1d, cnt_7d_ma, senti_1d_avg, senti_7d_avg
      FROM public.vw_news_daily_counts
     WHERE asset = %s
       AND (%s IS NULL OR date >= %s::date)
       AND (%s IS NULL OR date <= %s::date)
     ORDER BY date ASC;
    """
    dsn = _get_dsn()
    with psycopg2.connect(dsn) as conn, conn.cursor(
        cursor_factory=psycopg2.extras.DictCursor
    ) as cur:
        cur.execute(sql, (asset, date_from, date_from, date_to, date_to))
        rows = cur.fetchall()

    labels: List[str] = []
    cnt_1d: List[int] = []
    cnt_7d: List[Optional[float]] = []
    senti_1d: List[Optional[float]] = []
    senti_7d: List[Optional[float]] = []

    for r in rows:
        labels.append(r["date"].isoformat())
        cnt_1d.append(int(r["cnt_1d"]))
        cnt_7d.append(float(r["cnt_7d_ma"]) if r["cnt_7d_ma"] is not None else None)
        senti_1d.append(float(r["senti_1d_avg"]) if r["senti_1d_avg"] is not None else None)
        senti_7d.append(float(r["senti_7d_avg"]) if r["senti_7d_avg"] is not None else None)

    return {
        "labels": labels,
        "series": {
            "cnt_1d": cnt_1d,
            "cnt_7d_ma": cnt_7d,
            "senti_1d_avg": senti_1d,
            "senti_7d_avg": senti_7d,
        },
    }


def fetch_event_impact(
    event_tag: str,
    asset: str = "USDJPY",
    window: Tuple[int, int] = (-3, 3),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    anchors: vw_news_event_tags から event_tag 出現日
    joined : 各 anchor に対し、相対ウィンドウ内の日次件数/感情を join
    返却   : 相対日ごとの平均 (cnt_avg / senti_avg) とアンカー一覧
    """
    start_off, end_off = window
    dsn = _get_dsn()

    # アンカー日抽出（distinct）
    sql_anchors = """
    SELECT DISTINCT date
      FROM vw_news_event_tags
     WHERE asset = %s
       AND inferred_event_tag = %s
       AND (%s IS NULL OR date >= %s::date)
       AND (%s IS NULL OR date <= %s::date)
     ORDER BY date;
    """
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql_anchors, (asset, event_tag, date_from, date_from, date_to, date_to))
        anchors = [r[0] for r in cur.fetchall()]

    # 相対ウィンドウで平均集計（PostgreSQL: date - date は日数整数）
    sql_rel = """
    WITH anchors AS (
      SELECT DISTINCT date
        FROM public.vw_news_event_tags
       WHERE asset = %(asset)s
         AND inferred_event_tag = %(tag)s
         AND (%(df)s IS NULL OR date >= %(df)s::date)
         AND (%(dt)s IS NULL OR date <= %(dt)s::date)
    ),
    joined AS (
      SELECT (d.date - a.date) AS rel_day, d.cnt_1d, d.senti_1d_avg
        FROM anchors a
        JOIN vw_news_daily_counts d
          ON d.asset = %(asset)s
         AND d.date BETWEEN a.date + %(start)s AND a.date + %(end)s
    )
    SELECT rel_day::int, AVG(cnt_1d)::float AS cnt_avg, AVG(senti_1d_avg)::float AS senti_avg
      FROM joined
     GROUP BY rel_day
     ORDER BY rel_day;
    """
    params = {
        "asset": asset,
        "tag": event_tag,
        "df": date_from,
        "dt": date_to,
        "start": start_off,
        "end": end_off,
    }
    rel_labels: List[int] = []
    cnt_avg: List[float] = []
    senti_avg: List[float] = []
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql_rel, params)
        for rel_day, cavg, savg in cur.fetchall():
            rel_labels.append(int(rel_day))
            cnt_avg.append(float(cavg) if cavg is not None else 0.0)
            senti_avg.append(float(savg) if savg is not None else 0.0)

    # 相対範囲に欠測があれば 0/0 で埋める（グラフを滑らかにする）
    full_labels = list(range(start_off, end_off + 1))
    label_to_idx = {k: i for i, k in enumerate(rel_labels)}
    cnt_series = [0.0] * len(full_labels)
    senti_series = [0.0] * len(full_labels)
    for i, rel in enumerate(full_labels):
        if rel in label_to_idx:
            j = label_to_idx[rel]
            cnt_series[i] = cnt_avg[j]
            senti_series[i] = senti_avg[j]

    return {
        "labels": full_labels,  # 相対日 -3..+3
        "series": {"cnt_avg": cnt_series, "senti_avg": senti_series},
        "anchors": [a.isoformat() for a in anchors],
    }
