#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trigger noctria_backtest_dag via Airflow REST API (preferred) or CLI fallback.
Env:
  AIRFLOW_BASE_URL   e.g. http://localhost:8080
  AIRFLOW_TOKEN      Airflow API auth token (Bearer)
Args (optional via env; or use --strategy-glob/--extra-args later if拡張):
  NOCTRIA_STRATEGY_GLOB  default: src/strategies/veritas_generated/**.py
  NOCTRIA_EXTRA_ARGS     default: ""
"""
import json
import os
import subprocess
import sys
from datetime import datetime

DAG_ID = "noctria_backtest_dag"

def trigger_via_rest(base_url: str, token: str, conf: dict) -> None:
    import urllib.request
    import urllib.error

    url = f"{base_url.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns"
    payload = json.dumps({
        "dag_run_id": f"manual__{datetime.utcnow().isoformat()}",
        "conf": conf,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[REST] status={resp.status}")
            print(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[REST] HTTPError {e.code}: {e.read().decode('utf-8')}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[REST] error: {e}", file=sys.stderr)
        raise

def trigger_via_cli(conf: dict) -> None:
    # Airflowコンテナ内 or PATHにairflowがある想定
    cmd = [
        "airflow", "dags", "trigger", DAG_ID,
        "--conf", json.dumps(conf, ensure_ascii=False),
    ]
    print(f"[CLI] $ {' '.join(cmd)}")
    subprocess.check_call(cmd)

def main():
    strategy_glob = os.getenv("NOCTRIA_STRATEGY_GLOB", "src/strategies/veritas_generated/**.py")
    extra_args = os.getenv("NOCTRIA_EXTRA_ARGS", "")
    conf = {
        "strategy_glob": strategy_glob,
        "extra_args": extra_args,
    }
    base_url = os.getenv("AIRFLOW_BASE_URL")
    token = os.getenv("AIRFLOW_TOKEN")

    if base_url and token:
        try:
            trigger_via_rest(base_url, token, conf)
            return 0
        except Exception:
            print("[WARN] REST failed. Falling back to CLI...", file=sys.stderr)

    # CLI fallback
    try:
        trigger_via_cli(conf)
        return 0
    except Exception as e:
        print(f"[ERROR] failed to trigger via CLI: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
