# airflow_docker/dags/veritas_recheck_all_dag.py
# -*- coding: utf-8 -*-
"""
🔁 Veritas 一括再評価 DAG
- GUI (/pdca/recheck_all) からの conf を受け取り、filters に基づき対象戦略を抽出
- 個別再評価DAG（veritas_recheck_dag）を TriggerDagRunOperator で並列起動
- フィルターは conf = {"filters": {...}, "reason": "...", "triggered_by": "GUI"} を想定

依存:
- Airflow 2.5+（Task Mapping使用）
- 個別再評価DAG: 環境変数 AIRFLOW_DAG_RECHECK で指定（デフォルト: "veritas_recheck_dag"）
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from airflow import DAG
from airflow.decorators import task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

# ==== 設定（環境変数で上書き可） ==========================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # <repo_root>
PDCA_LOG_DIR = PROJECT_ROOT / "data" / "pdca_logs" / "veritas_orders"
STRATEGIES_DIR = PROJECT_ROOT / "src" / "strategies"

DAG_ID_RECHECK_ALL = os.getenv("AIRFLOW_DAG_RECHECK_ALL", "veritas_recheck_all_dag")
DAG_ID_RECHECK_SINGLE = os.getenv("AIRFLOW_DAG_RECHECK", "veritas_recheck_dag")

DEFAULT_ARGS = {
    "owner": "noctria",
    "depends_on_past": False,
    "retries": 0,
}

# ==== ユーティリティ ======================================================
def _safe_to_float(x) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return None
        return float(x)
    except Exception:
        return None

def _load_pdca_logs() -> pd.DataFrame:
    """
    PDCAログ（CSV/JSON複数）を縦結合して標準列を補完。
    """
    if not PDCA_LOG_DIR.exists():
        return pd.DataFrame()

    frames: List[pd.DataFrame] = []
    for fname in sorted(PDCA_LOG_DIR.iterdir()):
        if not fname.is_file():
            continue
        try:
            if fname.suffix.lower() == ".csv":
                df = pd.read_csv(fname)
            elif fname.suffix.lower() == ".json":
                obj = json.loads(fname.read_text())
                df = pd.DataFrame(obj if isinstance(obj, list) else [obj])
            else:
                continue
            df["__source_file"] = fname.name
            frames.append(df)
        except Exception:
            # 壊れたファイルはスキップ
            continue

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # 必須列の補完
    for col in [
        "strategy", "evaluated_at",
        "winrate_old", "winrate_new",
        "maxdd_old", "maxdd_new",
        "trades_old", "trades_new",
        "tag", "notes",
    ]:
        if col not in df_all.columns:
            df_all[col] = None

    # 型・差分
    df_all["evaluated_at"] = pd.to_datetime(df_all["evaluated_at"], errors="coerce")
    for col in ["winrate_old", "winrate_new", "maxdd_old", "maxdd_new"]:
        df_all[col] = df_all[col].apply(_safe_to_float)

    df_all["winrate_diff"] = df_all.apply(
        lambda r: None
        if (r["winrate_old"] is None or r["winrate_new"] is None)
        else (r["winrate_new"] - r["winrate_old"]),
        axis=1,
    )
    df_all["maxdd_diff"] = df_all.apply(
        lambda r: None
        if (r["maxdd_old"] is None or r["maxdd_new"] is None)
        else (r["maxdd_new"] - r["maxdd_old"]),
        axis=1,
    )
    return df_all


def _apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df
    res = df.copy()

    # 期間
    df_from = filters.get("date_from")
    df_to = filters.get("date_to")
    if df_from:
        res = res[res["evaluated_at"] >= pd.to_datetime(df_from, errors="coerce")]
    if df_to:
        res = res[res["evaluated_at"] <= pd.to_datetime(df_to, errors="coerce") + pd.Timedelta(days=1)]

    # 勝率/最大DD
    wr_min = filters.get("winrate_diff_min")
    dd_max = filters.get("maxdd_diff_max")

    if wr_min is not None:
        try:
            wr_min = float(wr_min)
            res = res[res["winrate_diff"].fillna(-1e9) >= wr_min]
        except Exception:
            pass

    if dd_max is not None:
        try:
            dd_max = float(dd_max)
            # 改善（より小さい = 良い）を拾うには <=
            res = res[res["maxdd_diff"].fillna(1e9) <= dd_max]
        except Exception:
            pass

    # search
    s = (filters.get("search") or "").strip().lower()
    if s:
        for col in ["strategy", "tag", "notes", "__source_file"]:
            res[col] = res[col].astype(str)
        res = res[
            res["strategy"].str.lower().str.contains(s, na=False)
            | res["tag"].str.lower().str.contains(s, na=False)
            | res["notes"].str.lower().str.contains(s, na=False)
            | res["__source_file"].str.lower().str.contains(s, na=False)
        ]
    return res


def _fallback_strategies_from_repo() -> List[str]:
    """
    ログが無い/空のときは src/strategies/ 配下の .py を戦略候補として返す。
    _ で始まるファイルや __init__.py は除外。
    """
    if not STRATEGIES_DIR.exists():
        return []
    names: List[str] = []
    for p in STRATEGIES_DIR.glob("*.py"):
        if p.name.startswith("_") or p.name == "__init__.py":
            continue
        names.append(p.stem)  # 拡張子除去
    return sorted(set(names))


def _select_targets(conf: Dict[str, Any]) -> List[str]:
    """
    conf から filters を読み、対象戦略のリストを決定。
    - ログがあればフィルタ適用
    - なければリポジトリから戦略ファイル名を列挙
    """
    filters = (conf or {}).get("filters") or {}
    df = _load_pdca_logs()
    if not df.empty:
        dff = _apply_filters(df, filters)
        strategies = (
            dff["strategy"].dropna().astype(str).str.strip().tolist()
        )
        strategies = [s for s in strategies if s]
        if strategies:
            return sorted(set(strategies))
    # フォールバック
    return _fallback_strategies_from_repo()


# ==== DAG 定義 ==============================================================
with DAG(
    dag_id=DAG_ID_RECHECK_ALL,
    default_args=DEFAULT_ARGS,
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["noctria", "veritas", "pdca", "recheck"],
    description="GUIフィルターに基づく一括再評価の親DAG",
) as dag:

    @task(multiple_outputs=True)
    def read_conf(**context) -> Dict[str, Any]:
        """trigger時の conf を取り出して返す（空でも落とさない）"""
        ti = context["ti"]
        dag_run = ti.get_dagrun()
        conf = dag_run.conf or {}
        reason = conf.get("reason")
        filters = conf.get("filters", {})
        triggered_by = conf.get("triggered_by", "unknown")
        return {
            "conf": conf,
            "reason": reason,
            "filters": filters,
            "triggered_by": triggered_by,
        }

    @task
    def decide_targets(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        フィルタから対象戦略を決定し、TriggerDagRunOperator に渡す map ペイロードを作る。
        """
        conf = payload.get("conf") or {}
        reason = payload.get("reason")
        triggered_by = payload.get("triggered_by")
        strategies = _select_targets(conf)

        # TriggerDagRunOperator.expand(conf=[...]) 用のリストに整形
        items: List[Dict[str, Any]] = []
        for s in strategies:
            items.append(
                {
                    "strategy": s,
                    "reason": reason,
                    "triggered_by": triggered_by,
                    "parent_dag": DAG_ID_RECHECK_ALL,
                }
            )
        return items

    # Task Mapping で個別DAGを並列起動
    trigger_each = TriggerDagRunOperator.partial(
        task_id="trigger_recheck_each",
        trigger_dag_id=DAG_ID_RECHECK_SINGLE,
        reset_dag_run=False,
        wait_for_completion=False,
        poke_interval=5,
    ).expand(conf=decide_targets(read_conf()))

    # 依存は read_conf -> decide_targets -> trigger_each
    # TaskFlowの戻り値配線で自動的に張られるため明示依存は不要
