# airflow_docker/dags/veritas_generate_dag.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
🗓️ Airflow DAG: Veritas 戦略生成（KEEP-safe 版）

主な改善
- DAG 解析時は軽量：重依存は一切 import しない。実処理はタスク内で遅延 import。
- veritas.strategy_generator.run_generation に委譲（machina/LLM/テンプレを自動フォールバック）。
- すべての実行に trace_id を付与し、obs_event へ観測ログ送出（存在しなければ安全なダミーで代替）。
- GitHub への push は `src/scripts/push_generated_strategy.py` を PATHS 経由で確実に解決。
- 既存 dag_run.conf のキー互換（symbol/tag/target_metric など）を維持しつつ、pair/profile も受理。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# ============== 軽量ユーティリティ（遅延 import / PATHS / logger / obs） ==============


def _lazy_import(name: str):
    try:
        __import__(name)
        return __import__(name)
    except Exception:
        return None


def _paths() -> Dict[str, Path]:
    mod = _lazy_import("core.path_config") or _lazy_import("src.core.path_config")
    root = Path(__file__).resolve().parents[2]  # .../airflow_docker/
    if mod:
        return {
            "ROOT": getattr(mod, "ROOT", root.parent),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", root.parent / "logs"),
            "STRATEGIES_DIR": getattr(mod, "STRATEGIES_DIR", root.parent / "src" / "strategies"),
        }
    return {
        "ROOT": root.parent,
        "LOGS_DIR": root.parent / "logs",
        "STRATEGIES_DIR": root.parent / "src" / "strategies",
    }


def _logger():
    mod = _lazy_import("core.logger") or _lazy_import("src.core.logger")
    p = _paths()
    log_path = Path(p["LOGS_DIR"]) / "dags" / "veritas_generate_dag.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("VeritasGenerateDAG", log_path)  # type: ignore[attr-defined]
    import logging

    lg = logging.getLogger("VeritasGenerateDAG")
    if not lg.handlers:
        lg.setLevel(logging.INFO)
        fh = logging.FileHandler(str(log_path), encoding="utf-8")
        sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        lg.addHandler(fh)
        lg.addHandler(sh)
    return lg


def _obs():
    mod = _lazy_import("plan_data.observability") or _lazy_import("src.plan_data.observability")
    import datetime as dt

    def mk_trace_id():
        return dt.datetime.utcnow().strftime("trace_%Y%m%dT%H%M%S_%f")

    def obs_event(
        event: str,
        *,
        severity: str = "LOW",
        trace_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        # ダミー出力（本物があれば差し替えられる）
        msg = {
            "event": event,
            "severity": severity,
            "trace_id": trace_id,
            "meta": meta or {},
            "ts": dt.datetime.utcnow().isoformat(),
        }
        print("[OBS]", json.dumps(msg, ensure_ascii=False))

    if mod:
        mk_trace_id = getattr(mod, "mk_trace_id", mk_trace_id)  # type: ignore
        obs_event = getattr(mod, "obs_event", obs_event)  # type: ignore
    return mk_trace_id, obs_event


PATHS = _paths()
logger = _logger()
mk_trace_id, obs_event = _obs()


# ============== タスク実体（DAG 解析時は import しない） ==========================


def _normalize_pair(symbol: str) -> str:
    """USDJPY → USD/JPY のように揃える（簡易）"""
    s = (symbol or "").upper().replace(" ", "")
    if "/" in s:
        return s
    if len(s) == 6:  # USDJPY
        return f"{s[:3]}/{s[3:]}"
    return s or "USD/JPY"


def _generate_and_save_task(**context):
    # conf 読み取り（互換: symbol/tag/target_metric, 追加: pair/profile/model_dir/safe_mode/dry_run）
    dag_run = context.get("dag_run")
    conf: Dict[str, Any] = dag_run.conf if dag_run else {}
    decision_id = conf.get("decision_id", "NO_DECISION_ID")
    reason = conf.get("reason", "理由未指定")
    caller = conf.get("caller", "unknown")

    trace_id = mk_trace_id()
    obs_event(
        "dag.veritas_generate.start",
        trace_id=trace_id,
        meta={"decision_id": decision_id, "caller": caller, "reason": reason},
    )

    # 互換キー→内部 I/F へ
    symbol = conf.get("symbol")
    pair = _normalize_pair(conf.get("pair") or symbol or "USDJPY")
    tag = conf.get("tag", "default")
    profile = conf.get("profile")
    model_dir = conf.get("model_dir")  # 任意: ローカル LLM ディレクトリ
    safe_mode = bool(conf.get("safe_mode", False))
    dry_run = bool(conf.get("dry_run", False))  # 既定 False（本番は保存したい）

    logger.info(f"📜 [decision_id:{decision_id}] DAG実行 conf={conf}")

    # 遅延 import（重依存が内部にあっても DAG パースは安全）
    veritas_gen = _lazy_import("veritas.strategy_generator") or _lazy_import(
        "src.veritas.strategy_generator"
    )
    if not veritas_gen or not hasattr(veritas_gen, "run_generation"):
        logger.error(
            f"❌ [decision_id:{decision_id}] veritas.strategy_generator.run_generation が見つかりません"
        )
        raise RuntimeError("veritas.strategy_generator.run_generation not available")

    try:
        result: Dict[str, Any] = veritas_gen.run_generation(  # type: ignore[attr-defined]
            pair=pair,
            tag=tag,
            profile=profile,
            model_dir=model_dir,
            dry_run=dry_run,
            safe_mode=safe_mode,
            seed=None,
            out_dir=None,  # 既定: STRATEGIES_DIR/veritas_generated
        )
        saved = result.get("path")
        via = result.get("meta", {}).get("via")
        fallback = result.get("meta", {}).get("fallback")
        logger.info(
            f"🧠 [decision_id:{decision_id}] 生成完了 via={via} fallback={fallback} path={saved}"
        )
        obs_event(
            "dag.veritas_generate.done",
            trace_id=trace_id,
            meta={"decision_id": decision_id, "path": saved, "via": via, "fallback": fallback},
        )

        ti = context["ti"]
        ti.xcom_push(key="trigger_reason", value=reason)
        ti.xcom_push(key="decision_id", value=decision_id)
        ti.xcom_push(key="caller", value=caller)
        ti.xcom_push(key="saved_path", value=saved)
        ti.xcom_push(key="trace_id", value=trace_id)
        return saved or ""
    except Exception as e:
        logger.error(f"❌ [decision_id:{decision_id}] 生成処理で例外: {e}", exc_info=True)
        obs_event(
            "dag.veritas_generate.error",
            severity="HIGH",
            trace_id=trace_id,
            meta={"decision_id": decision_id, "exc": repr(e)},
        )
        raise


def _push_to_github_task(**context):
    import subprocess

    dag_run = context.get("dag_run")
    conf: Dict[str, Any] = dag_run.conf if dag_run else {}
    decision_id = conf.get("decision_id", "NO_DECISION_ID")
    trace_id = mk_trace_id()

    # スクリプトの実際の位置を PATHS から安全に解決
    script = PATHS["ROOT"] / "src" / "scripts" / "push_generated_strategy.py"
    if not script.is_file():
        logger.warning(
            f"⚠️ [decision_id:{decision_id}] push スクリプトが見つかりません: {script} → スキップ（HOLD）"
        )
        obs_event(
            "dag.veritas_generate.push_skipped",
            trace_id=trace_id,
            meta={"reason": "script_not_found", "script": str(script)},
        )
        return "skipped"

    try:
        # そのまま実行。失敗したら例外でリトライ対象。
        subprocess.run(["python3", str(script)], check=True)
        logger.info(f"✅ [decision_id:{decision_id}] GitHubへのPushが完了しました。")
        obs_event("dag.veritas_generate.push_done", trace_id=trace_id, meta={"script": str(script)})
        return "ok"
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ [decision_id:{decision_id}] GitHub Pushで失敗: {e}", exc_info=True)
        obs_event(
            "dag.veritas_generate.push_error",
            severity="HIGH",
            trace_id=trace_id,
            meta={"exc": repr(e)},
        )
        raise


# ============== DAG 本体 =======================================================

with DAG(
    dag_id="veritas_generate_dag",
    default_args={
        "owner": "Noctria",
        "start_date": datetime(2025, 6, 1),
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "ml", "generator"],
) as dag:
    generate_task = PythonOperator(
        task_id="generate_and_save_strategy",
        python_callable=_generate_and_save_task,
        provide_context=True,
    )

    push_task = PythonOperator(
        task_id="push_strategy_to_github",
        python_callable=_push_to_github_task,
        provide_context=True,
    )

    generate_task >> push_task
