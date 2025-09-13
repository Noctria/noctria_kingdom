# airflow_docker/dags/noctria_backtest_dag.py
from __future__ import annotations

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import json
import os
import subprocess
import sys
from typing import Any, Dict


# ===== ユーティリティ =====
def _mk_outdir(run_id: str) -> str:
    outdir = f"/opt/airflow/backtests/{run_id}"
    os.makedirs(outdir, exist_ok=True)
    return outdir


def _write_json(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _load_conf(context) -> Dict[str, Any]:
    """dag_run.conf を吸収し、デフォルトを埋める"""
    conf = dict(context.get("dag_run").conf or {})
    # 実行対象戦略（グロブ）
    conf.setdefault("strategy_glob", "src/strategies/veritas_generated/**.py")
    # 追加引数（文字列）
    conf.setdefault("extra_args", "")
    return conf


def _heavy_env_ready() -> bool:
    """重依存が使えるか軽く判定（torch が import できるだけでもOK）"""
    try:
        import importlib

        importlib.import_module("torch")  # noqa: F401
        return True
    except Exception:
        return False


# ===== 実バックテスト or ダミー =====
def backtest_entry(**context):
    """
    可能なら実バックテストを実行。
    - airflow_docker/scripts/veritas_local_test.py が存在
    - torch が import 可能
    いずれか満たさない場合はダミーにフォールバック。
    すべての成果物は /opt/airflow/backtests/<run_id>/ に集約。
    """
    run_id = context["run_id"]
    conf = _load_conf(context)
    outdir = _mk_outdir(run_id)

    # conf を保存（トレース用）
    _write_json(os.path.join(outdir, "conf.json"), conf)

    script_path = "/opt/airflow/airflow_docker/scripts/veritas_local_test.py"
    script_repo_path = "airflow_docker/scripts/veritas_local_test.py"  # 開発時の相対パスも試す

    # 実スクリプトのパスを解決
    candidate_paths = [script_path, os.path.abspath(script_repo_path)]
    real_script = next((p for p in candidate_paths if os.path.exists(p)), None)

    heavy_ok = _heavy_env_ready()
    will_run_real = heavy_ok and real_script is not None

    meta = {
        "run_id": run_id,
        "mode": "real" if will_run_real else "dummy",
        "script": real_script,
        "heavy_ok": heavy_ok,
    }

    try:
        if will_run_real:
            # 実バックテスト: veritas_local_test.py を呼ぶ
            cmd = [
                sys.executable,
                real_script,
            ]
            # veritas_local_test.py 側で --pattern/追加引数を扱っていない場合もあるので、
            # ここでは環境変数で渡す（将来引数対応したら cmd に追加してOK）
            env = os.environ.copy()
            env["NOCTRIA_STRATEGY_GLOB"] = str(conf.get("strategy_glob", ""))
            env["NOCTRIA_EXTRA_ARGS"] = str(conf.get("extra_args", ""))

            log_path = os.path.join(outdir, "stdout.txt")
            with open(log_path, "w", encoding="utf-8") as logf:
                proc = subprocess.run(
                    cmd,
                    cwd=os.getcwd(),
                    env=env,
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            meta["returncode"] = proc.returncode
            meta["stdout_path"] = log_path

            # 成功扱い（スクリプト内部で ImportError スキップ exit(0) の想定）
            if proc.returncode == 0:
                result = {
                    "ok": True,
                    "msg": "Real backtest executed (see stdout.txt)",
                    "conf": conf,
                    "mode": "real",
                    "stdout_path": log_path,
                }
                _write_json(os.path.join(outdir, "result.json"), result)
            else:
                # 実行が失敗したらダミーにフォールバックせずエラーとして返す
                result = {
                    "ok": False,
                    "msg": "Real backtest failed (see stdout.txt)",
                    "conf": conf,
                    "mode": "real",
                    "stdout_path": log_path,
                }
                _write_json(os.path.join(outdir, "result.json"), result)
                # Airflow task は失敗にする
                raise RuntimeError("Real backtest failed")

        else:
            # ダミー
            result = {
                "ok": True,
                "msg": "Dummy backtest succeeded (heavy env not available)",
                "conf": conf,
                "mode": "dummy",
            }
            _write_json(os.path.join(outdir, "result.json"), result)

        # XCom に主要パスを返す
        return {
            "result_path": f"{outdir}/result.json",
            "outdir": outdir,
            "meta": meta,
        }

    except Exception as e:
        # 失敗時もメタを書き出しておく
        meta["error"] = str(e)
        _write_json(os.path.join(outdir, "meta.json"), meta)
        raise


# ===== DAG 定義 =====
default_args = {
    "owner": "noctria",
    "retries": 0,
}

with DAG(
    dag_id="noctria_backtest_dag",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # API専用
    catchup=False,
    dagrun_timeout=timedelta(minutes=10),
    tags=["noctria", "backtest"],
) as dag:
    run = PythonOperator(
        task_id="run_backtest",
        python_callable=backtest_entry,
        provide_context=True,  # Airflow 2.x 互換。3.x では context は自動渡し
    )
