# dags/noctria_backtest_dag.py
from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import json, subprocess, os, textwrap

def run_backtest(**context):
    conf = context["dag_run"].conf or {}
    # GitHubから渡すメタ
    repo    = conf.get("repo")
    pr      = conf.get("pr")
    branch  = conf.get("branch")
    title   = conf.get("title")
    sha     = conf.get("sha")
    merger  = conf.get("merger")

    # ここで本当のバックテスト処理を呼ぶ（暫定はechoだけ）
    # 例: subprocess.check_call(["python", "codex/tools/run_backtest.py", "--branch", branch, "--sha", sha])
    print("=== Backtest Input ===")
    print(json.dumps(conf, ensure_ascii=False, indent=2))

    # 成果物の例：/opt/airflow/backtests/<run_id>/result.json に保存する等
    run_id = context["run_id"]
    outdir = f"/opt/airflow/backtests/{run_id}"
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump({"ok": True, "repo": repo, "pr": pr, "sha": sha}, f)

    # 必要ならXCom等で返す
    return {"result_path": f"{outdir}/result.json"}

default_args = {
    "owner": "noctria",
    "retries": 0,
}

with DAG(
    dag_id="noctria_backtest_dag",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,            # 予約実行なし（APIからのみ）
    catchup=False,
    dagrun_timeout=timedelta(hours=2), # タイムアウト保険
    tags=["noctria", "backtest"],
) as dag:

    backtest = PythonOperator(
        task_id="run_backtest",
        python_callable=run_backtest,
        provide_context=True,
    )
