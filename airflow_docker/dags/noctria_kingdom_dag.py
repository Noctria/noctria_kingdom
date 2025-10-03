# [NOCTRIA_CORE_REQUIRED]
# airflow_docker/dags/noctria_kingdom_dag.py
#!/usr/bin/env python3
# coding: utf-8

"""
👑 Noctria Kingdom Royal Council DAG (Airflow 2.6 互換版)
- 市場観測 → 御前会議 → 王命記録
- GUI/REST の conf（reason 等）を kwargs から受け取る
- get_current_context は使わず、kwargs の context を参照

統合ポイント:
- trace_id の起票とXCom伝搬
- observability(log_*) を優先し、失敗時はSTDOUTへJSONフォールバック
- ensure_import_path() を存在すれば呼び出し
"""

import json
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

# ---- src パスの前提下での正規 import ----
from src.core.path_config import LOGS_DIR  # 既存のまま利用

# --- 追加: 安全な import path ブートストラップ（存在すれば呼び出し） -----------------
try:
    from src.core.path_config import ensure_import_path  # type: ignore

    ensure_import_path()  # 引数なしでもプロジェクトルートを解決する実装を想定（なければ内部で無害にNO-OP）
except Exception:
    pass
    # 失敗してもDAGパースを阻害しない
    pass

# --- 追加: observability / trace は遅延失敗に備えてグレースフルに扱う ---------------
try:
    from src.plan_data import observability as obs  # type: ignore
except Exception:  # observability が無い/壊れていても運行継続
    obs = None  # type: ignore

try:
    from src.plan_data import trace as trace_mod  # type: ignore
except Exception:
    trace_mod = None  # type: ignore

default_args = {
    "owner": "KingNoctria",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# --- 追加: 観測ログの薄いラッパ（obs 優先、失敗時は STDOUT JSON） -------------------
def _log(level: str, msg: str, extra: dict | None = None, trace_id: str | None = None) -> None:
    extra = extra or {}
    try:
        if obs is not None:
            if level == "info":
                obs.log_info(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            elif level in ("warn", "warning"):
                obs.log_warn(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            elif level == "error":
                obs.log_error(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            else:
                obs.log_debug(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            return
    except Exception:
        pass
        # fallthrough to stdout

    # フォールバック: JSON を stdout（Airflow task log）へ
    print(
        json.dumps(
            {
                "ts": datetime.utcnow().isoformat(),
                "level": level.upper(),
                "msg": msg,
                "trace_id": trace_id,
                "extra": extra,
            },
            ensure_ascii=False,
        )
    )


def _new_trace_id() -> str:
    try:
        if trace_mod is not None and hasattr(trace_mod, "new_trace_id"):
            return trace_mod.new_trace_id()  # type: ignore[attr-defined]
    except Exception:
        pass
    # フォールバック（衝突低確率で十分）
    return f"trace-{datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')}"


def _serialize_for_json(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(x) for x in obj]
    return obj


def _get_reason_from_conf(kwargs) -> str:
    dag_run = kwargs.get("dag_run")
    if dag_run and getattr(dag_run, "conf", None):
        return dag_run.conf.get("reason", "理由未指定")
    return "理由未指定"


with DAG(
    dag_id="noctria_kingdom_royal_council_dag",
    default_args=default_args,
    description="市場を観測し、御前会議を開き、王の最終判断を下すための中心DAG",
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=["noctria", "kingdom", "royal_council"],
) as dag:

    def fetch_market_data_task(**kwargs):
        logger = logging.getLogger("MarketObserver")
        logger.setLevel(logging.INFO)

        reason = _get_reason_from_conf(kwargs)
        # trace_id 起票（ここを起点にXComで伝搬）
        trace_id = _new_trace_id()
        _log("info", "【市場観測・発令理由】" + str(reason), {"phase": "fetch"}, trace_id)

        # ダミーデータ（本番は fetcher へ置換可）
        dummy_hist = pd.DataFrame({"Close": np.random.normal(loc=150, scale=2, size=100)})
        dummy_hist["returns"] = dummy_hist["Close"].pct_change()

        market_data = {
            "price": float(150.50 + np.random.randn()),
            "previous_price": float(150.48 + np.random.randn()),
            "volume": int(np.random.randint(100, 300)),
            "volatility": float(np.random.uniform(0.1, 0.3)),
            "sma_5_vs_20_diff": float(np.random.uniform(-0.1, 0.1)),
            "macd_signal_diff": float(np.random.uniform(-0.05, 0.05)),
            "trend_strength": float(np.random.uniform(0.3, 0.8)),
            "trend_prediction": str(np.random.choice(["bullish", "bearish", "neutral"])),
            "rsi_14": float(np.random.uniform(30, 70)),
            "stoch_k": float(np.random.uniform(20, 80)),
            "momentum": float(np.random.uniform(0.4, 0.9)),
            "bollinger_upper_dist": float(np.random.uniform(-0.05, 0.05)),
            "bollinger_lower_dist": float(np.random.uniform(-0.05, 0.05)),
            "sentiment": float(np.random.uniform(0.3, 0.9)),
            "order_block": float(np.random.uniform(0.2, 0.8)),
            "liquidity_ratio": float(np.random.uniform(0.8, 1.5)),
            "symbol": "USDJPY",
            "interest_rate_diff": 0.05,
            "cpi_change_rate": 0.03,
            "news_sentiment_score": float(np.random.uniform(0.4, 0.8)),
            "spread": float(np.random.uniform(0.01, 0.02)),
            "historical_data": dummy_hist.to_json(date_format="iso"),
            "trigger_reason": reason,
            # 追加: trace_id をデータに同梱（会議側で利用可）
            "trace_id": trace_id,
        }

        # XCom へ格納
        ti = kwargs["ti"]
        ti.xcom_push(key="market_data", value=market_data)
        ti.xcom_push(key="trace_id", value=trace_id)

        _log(
            "info",
            "市場の観測完了。データを御前会議に提出します。",
            {"size": len(dummy_hist)},
            trace_id,
        )
        logger.info("市場の観測完了。データを御前会議に提出します。")
        return market_data

    def hold_council_task(**kwargs):
        # 遅延 import（DAGパースを軽くする）
        from src.core.king_noctria import KingNoctria

        logger = logging.getLogger("RoyalCouncil")
        logger.setLevel(logging.INFO)

        reason = _get_reason_from_conf(kwargs)
        ti = kwargs["ti"]

        # XCom から受領
        market_data = ti.xcom_pull(key="market_data", task_ids="fetch_market_data")
        trace_id = ti.xcom_pull(key="trace_id", task_ids="fetch_market_data") or _new_trace_id()

        _log("info", "【御前会議・発令理由】" + str(reason), {"phase": "council"}, trace_id)

        if not market_data:
            _log("error", "市場データが取得できなかったため、会議を中止します。", None, trace_id)
            logger.error("市場データが取得できなかったため、会議を中止します。")
            raise ValueError("Market data not found in XComs.")

        # 復元
        hist_json = market_data.get("historical_data")
        if hist_json:
            try:
                market_data["historical_data"] = pd.read_json(hist_json)
            except Exception as e:
                _log(
                    "warn",
                    "historical_data の復元に失敗（空DFで継続）",
                    {"error": str(e)},
                    trace_id,
                )
                market_data["historical_data"] = pd.DataFrame()

        # KingNoctria 呼び出し（trace_id は market_data に入っているため、内部で拾える設計を想定）
        king = KingNoctria()
        council_report = king.hold_council(market_data)

        # 追加: report にも trace 情報を残す
        if isinstance(council_report, dict):
            council_report.setdefault("trace_id", trace_id)
            council_report.setdefault("trigger_reason", reason)

        _log(
            "info",
            f"会議終了。王の最終判断: {council_report.get('final_decision', 'N/A') if isinstance(council_report, dict) else 'N/A'}",
            {"keys": list(council_report.keys()) if isinstance(council_report, dict) else None},
            trace_id,
        )

        ti.xcom_push(key="council_report", value=council_report)
        return council_report

    def log_decision_task(**kwargs):
        logger = logging.getLogger("RoyalScribe")
        logger.setLevel(logging.INFO)

        reason = _get_reason_from_conf(kwargs)
        ti = kwargs["ti"]

        report = ti.xcom_pull(key="council_report", task_ids="hold_council")
        trace_id = ti.xcom_pull(key="trace_id", task_ids="fetch_market_data") or _new_trace_id()

        if not report:
            _log("warn", "記録すべき報告書が存在しませんでした。", {"phase": "scribe"}, trace_id)
            logger.warning("記録すべき報告書が存在しませんでした。")
            return

        # 既存ロジック維持＋追記
        if isinstance(report, dict):
            report["trigger_reason"] = reason
            report.setdefault("trace_id", trace_id)

        serializable = _serialize_for_json(report)

        log_file_path = (
            LOGS_DIR
            / "kingdom_council_reports"
            / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_report.json"
        )
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=4)

        _log("info", "王命を公式記録として書庫に納めました", {"path": str(log_file_path)}, trace_id)
        logger.info(f"王命を公式記録として書庫に納めました: {log_file_path}")

    task_fetch_data = PythonOperator(
        task_id="fetch_market_data",
        python_callable=fetch_market_data_task,
        provide_context=True,  # Airflow 2.6系でも安全に kwargs を渡す
    )

    task_hold_council = PythonOperator(
        task_id="hold_council",
        python_callable=hold_council_task,
        provide_context=True,
    )

    task_log_decision = PythonOperator(
        task_id="log_decision",
        python_callable=log_decision_task,
        provide_context=True,
    )

    task_fetch_data >> task_hold_council >> task_log_decision
