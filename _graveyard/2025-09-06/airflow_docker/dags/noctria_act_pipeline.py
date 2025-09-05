# =========================
# Noctria Act 層 自動化 一式
#  - Airflow DAG: 再評価結果の集計→採用判定→Git Push→Gitタグ付け→Decision Registry記録
#  - 最小依存で動くよう遅延インポート＆例外ベストエフォート
#  - 既存構成（/src, /airflow_docker/dags, /strategies/veritas_generated など）に合わせた相対パス
# =========================

# -------------------------------------------------------------------
# File: airflow_docker/dags/noctria_act_pipeline.py
# -------------------------------------------------------------------
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏰 Noctria Act Pipeline DAG
- 目的: 「再評価結果の集計 → 採用判定 → Git Push → タグ付け → レジストリ記録」を自動化
- 実行例: 手動トリガ時に conf で閾値や対象期間を上書き可能
    {
      "WINRATE_MIN_DELTA_PCT": 3.0,
      "MAX_DD_MAX_DELTA_PCT": 2.0,
      "LOOKBACK_DAYS": 30,
      "DRY_RUN": false,
      "TAG_PREFIX": "veritas",
      "RELEASE_NOTES": "PDCA auto adopt"
    }
"""

import os
import sys
from datetime import datetime, timedelta

from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

# --- Airflowからsrc/配下をimport可能に ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

DEFAULT_ARGS = {
    "owner": "noctria",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

DAG_ID = "noctria_act_pipeline"

def _collect_recheck_summary(**context):
    # 遅延インポート
    from pdca.selector import collect_candidates_summary
    conf = context["dag_run"].conf or {}
    lookback_days = int(conf.get("LOOKBACK_DAYS", 30))
    summary = collect_candidates_summary(lookback_days=lookback_days)
    # XCom返却
    return summary

def _decide_adoption(**context):
    from pdca.selector import choose_best_candidate
    conf = context["dag_run"].conf or {}
    summary = context["ti"].xcom_pull(task_ids="collect_recheck_summary")
    if not summary:
        return {"adopt": False, "reason": "no_summary"}
    params = {
        "WINRATE_MIN_DELTA_PCT": float(conf.get("WINRATE_MIN_DELTA_PCT", 3.0)),
        "MAX_DD_MAX_DELTA_PCT": float(conf.get("MAX_DD_MAX_DELTA_PCT", 2.0)),
        "MIN_TRADES": int(conf.get("MIN_TRADES", 30)),
    }
    decision = choose_best_candidate(summary=summary, **params)
    return decision

def _adopt_and_push(**context):
    from pdca.apply_adoption import adopt_and_push
    conf = context["dag_run"].conf or {}
    decision = context["ti"].xcom_pull(task_ids="decide_adoption")
    dry_run = bool(conf.get("DRY_RUN", False))
    tag_prefix = str(conf.get("TAG_PREFIX", "veritas"))
    release_notes = str(conf.get("RELEASE_NOTES", "PDCA auto adopt"))
    result = adopt_and_push(decision=decision, dry_run=dry_run, tag_prefix=tag_prefix, release_notes=release_notes)
    return result

def _record_decision(**context):
    from core.decision_registry import DecisionRegistry
    decision = context["ti"].xcom_pull(task_ids="decide_adoption") or {}
    adopt_result = context["ti"].xcom_pull(task_ids="adopt_and_push") or {}
    try:
        reg = DecisionRegistry()
        reg.record(
            phase="act",
            status="completed" if adopt_result.get("ok") else "skipped",
            payload={
                "decision": decision,
                "adopt_result": adopt_result,
                "dag_run_id": context["run_id"],
            },
        )
        return {"recorded": True}
    except Exception as e:
        # ベストエフォートで継続
        return {"recorded": False, "error": str(e)}

with DAG(
    dag_id=DAG_ID,
    description="Noctria PDCA Act: adopt & push & tag",
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # 手動 or 上位DAGからトリガ
    start_date=datetime(2025, 8, 1),
    catchup=False,
    tags=["noctria", "pdca", "act"],
) as dag:

    t_collect = PythonOperator(
        task_id="collect_recheck_summary",
        python_callable=_collect_recheck_summary,
        provide_context=True,
    )

    t_decide = PythonOperator(
        task_id="decide_adoption",
        python_callable=_decide_adoption,
        provide_context=True,
    )

    t_adopt = PythonOperator(
        task_id="adopt_and_push",
        python_callable=_adopt_and_push,
        provide_context=True,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    t_record = PythonOperator(
        task_id="record_decision",
        python_callable=_record_decision,
        provide_context=True,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    t_collect >> t_decide >> t_adopt >> t_record


# -------------------------------------------------------------------
# File: src/pdca/selector.py
# -------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
PDCA 再評価結果の集計と、採用候補の選定ロジック。
- データソース:
  1) data/pdca_logs/veritas_orders/*.jsonl （過去スレで言及の既存ログ構成を想定）
  2) 将来的にDB (obs_* テーブル) へ切替可能
"""

from __future__ import annotations
import os
import json
from glob import glob
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PDCA_DIR = os.path.join(PROJECT_ROOT, "..", "data", "pdca_logs", "veritas_orders")

def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows

def _list_jsonl_files(lookback_days: int) -> List[str]:
    if not os.path.exists(DATA_PDCA_DIR):
        return []
    now = datetime.utcnow()
    files = glob(os.path.join(DATA_PDCA_DIR, "*.jsonl"))
    out = []
    for p in files:
        try:
            ts = datetime.utcfromtimestamp(os.path.getmtime(p))
            if ts >= now - timedelta(days=lookback_days):
                out.append(p)
        except Exception:
            continue
    return sorted(out)

def collect_candidates_summary(lookback_days: int = 30) -> Dict[str, Any]:
    """
    期間内の再評価結果を集約して、戦略ID毎にサマリー化。
    期待するログのキー例:
      - strategy_id, winrate_pct, max_drawdown_pct, num_trades, params, metrics, created_at
    """
    files = _list_jsonl_files(lookback_days=lookback_days)
    summary: Dict[str, Dict[str, Any]] = {}
    for fp in files:
        for row in _read_jsonl(fp):
            sid = str(row.get("strategy_id") or row.get("strategy_name") or "unknown")
            if sid not in summary:
                summary[sid] = {
                    "strategy_id": sid,
                    "trials": [],
                    "best": None,
                }
            trial = {
                "winrate_pct": float(row.get("winrate_pct", 0.0)),
                "max_drawdown_pct": float(row.get("max_drawdown_pct", 0.0)),
                "num_trades": int(row.get("num_trades", 0)),
                "params": row.get("params") or {},
                "metrics": row.get("metrics") or {},
                "created_at": row.get("created_at"),
                "source_log": os.path.basename(fp),
            }
            summary[sid]["trials"].append(trial)

    # 各戦略のベストを選ぶ（winrate高/ DD低 / 取引数下限）
    for sid, s in summary.items():
        best = None
        for t in s["trials"]:
            if t["num_trades"] <= 0:
                continue
            if best is None:
                best = t
                continue
            if (t["winrate_pct"], -t["max_drawdown_pct"], t["num_trades"]) > (best["winrate_pct"], -best["max_drawdown_pct"], best["num_trades"]):
                best = t
        s["best"] = best
    return {"lookback_days": lookback_days, "candidates": summary}

def choose_best_candidate(
    summary: Dict[str, Any],
    WINRATE_MIN_DELTA_PCT: float = 3.0,
    MAX_DD_MAX_DELTA_PCT: float = 2.0,
    MIN_TRADES: int = 30,
) -> Dict[str, Any]:
    """
    採用基準:
      - 勝率: 既存（ベースライン）比で +WINRATE_MIN_DELTA_PCT 以上
      - 最大DD: 既存比で +MAX_DD_MAX_DELTA_PCT を超えない
      - 取引数 >= MIN_TRADES
    既存ベースラインは当面、「各strategy_idの直近メトリクスの中央値」を簡易的に推定。
    """
    # ここでは簡易に、trialsの中央値をベースラインとして擬似比較（本番はDBや専用表から取得推奨）
    import statistics

    cand = summary.get("candidates", {})
    best_choice = None
    reasons: List[str] = []
    for sid, s in cand.items():
        if not s.get("trials"):
            continue
        winrates = [float(t["winrate_pct"]) for t in s["trials"] if t["num_trades"] >= MIN_TRADES]
        dds = [float(t["max_drawdown_pct"]) for t in s["trials"] if t["num_trades"] >= MIN_TRADES]
        if not winrates or not dds:
            continue
        baseline_win = statistics.median(winrates)
        baseline_dd = statistics.median(dds)
        best = s.get("best")
        if not best:
            continue
        # 増分
        delta_win = best["winrate_pct"] - baseline_win
        delta_dd = best["max_drawdown_pct"] - baseline_dd
        pass_win = delta_win >= WINRATE_MIN_DELTA_PCT
        pass_dd = delta_dd <= MAX_DD_MAX_DELTA_PCT
        pass_trades = best["num_trades"] >= MIN_TRADES
        if pass_win and pass_dd and pass_trades:
            if best_choice is None:
                best_choice = {"strategy_id": sid, "baseline": {"win": baseline_win, "dd": baseline_dd}, "best": best}
            else:
                # さらに優れたものを選ぶ
                if (best["winrate_pct"], -best["max_drawdown_pct"], best["num_trades"]) > (
                    best_choice["best"]["winrate_pct"], -best_choice["best"]["max_drawdown_pct"], best_choice["best"]["num_trades"]
                ):
                    best_choice = {"strategy_id": sid, "baseline": {"win": baseline_win, "dd": baseline_dd}, "best": best}
        else:
            reasons.append(f"{sid}: winΔ={delta_win:.2f} ddΔ={delta_dd:.2f} trades={best['num_trades']} -> pass_win={pass_win} pass_dd={pass_dd} pass_trades={pass_trades}")

    if best_choice:
        return {"adopt": True, "choice": best_choice, "reasons": reasons}
    return {"adopt": False, "reasons": reasons}


# -------------------------------------------------------------------
# File: src/pdca/apply_adoption.py
# -------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
採用決定を受けて:
 - 戦略ファイルの保存（veritas_generated配下）
 - Git commit / push / tag
 - adopt報告用の結果を返却
"""

from __future__ import annotations
import os
import json
import time
from typing import Dict, Any
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGIES_DIR = os.path.join(PROJECT_ROOT, "strategies", "veritas_generated")

def _safe_mkdir(p: str):
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)

def _make_strategy_filename(strategy_id: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base = strategy_id.replace("/", "_").replace(" ", "_")
    return f"{base}_{ts}.py"

def _render_strategy_stub(strategy_id: str, params: Dict[str, Any], metrics: Dict[str, Any]) -> str:
    # ここではスタブ戦略を生成：実環境ではVeritas出力やテンプレート合成に置き換え可能
    return f'''# Auto-generated by PDCA Act
# strategy_id: {strategy_id}
# generated_at: {datetime.utcnow().isoformat()}Z

from typing import Any, Dict

class Strategy_{strategy_id.replace("-", "_").replace(" ", "_")}:
    def __init__(self, params: Dict[str, Any]):
        self.params = params

    def propose(self, market):
        # TODO: implement logic based on params
        return []

PARAMS = {json.dumps(params, ensure_ascii=False, indent=2)}
METRICS = {json.dumps(metrics, ensure_ascii=False, indent=2)}
'''

def adopt_and_push(decision: Dict[str, Any], dry_run: bool = False, tag_prefix: str = "veritas", release_notes: str = "") -> Dict[str, Any]:
    from core.git_utils import GitHelper

    if not decision or not decision.get("adopt"):
        return {"ok": False, "reason": "no_adoption"}

    choice = decision["choice"]
    sid = choice["strategy_id"]
    best = choice["best"]
    params = best.get("params") or {}
    metrics = {
        "winrate_pct": best.get("winrate_pct"),
        "max_drawdown_pct": best.get("max_drawdown_pct"),
        "num_trades": best.get("num_trades"),
        "baseline_win": decision.get("baseline", {}).get("win") if decision.get("baseline") else choice.get("baseline", {}).get("win"),
        "baseline_dd": decision.get("baseline", {}).get("dd") if decision.get("baseline") else choice.get("baseline", {}).get("dd"),
    }

    _safe_mkdir(STRATEGIES_DIR)
    filename = _make_strategy_filename(sid)
    path = os.path.join(STRATEGIES_DIR, filename)
    code = _render_strategy_stub(sid, params, metrics)

    if dry_run:
        return {"ok": True, "dry_run": True, "strategy_file": path, "tag": None}

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)

    gh = GitHelper()
    msg = f"feat(strategy): adopt {sid} via PDCA Act\n\n{json.dumps(metrics, ensure_ascii=False, indent=2)}"
    gh.add_commit_push(paths=[path], message=msg)

    tag = gh.create_tag_and_push(prefix=tag_prefix, annotation=release_notes or f"Adopt {sid}")
    return {"ok": True, "strategy_file": path, "tag": tag}
