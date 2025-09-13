#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trigger noctria_backtest_dag via Airflow REST API (preferred) or CLI fallback.

Env (any of the following auth styles work):

# Base URL (required for REST)
  AIRFLOW_BASE_URL       e.g. http://localhost:8080

# Bearer token auth (if available; takes priority over Basic)
  AIRFLOW_TOKEN          e.g. eyJhbGciOi...

# Basic auth (OSS Airflowで一般的)
  AIRFLOW_USER           e.g. admin
  AIRFLOW_PASSWORD       e.g. admin

# Optional conf to pass to DAG
  NOCTRIA_STRATEGY_GLOB  default: src/strategies/veritas_generated/**.py
  NOCTRIA_EXTRA_ARGS     default: ""

If REST fails (or AIRFLOW_BASE_URL が未設定)、`airflow dags trigger` をCLIで試みます。
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

DAG_ID = "noctria_backtest_dag"
DEFAULT_TIMEOUT = 30  # seconds


def trigger_via_rest(
    base_url: str,
    conf: dict,
    token: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> None:
    import urllib.request
    import urllib.error

    url = f"{base_url.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns"
    payload = json.dumps(
        {"dag_run_id": f"manual__{datetime.utcnow().isoformat()}", "conf": conf},
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    # Auth header (Bearer > Basic > none)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    elif user and password:
        b = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {b}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"[REST] status={resp.status}")
            print(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[REST] HTTPError {e.code}: {body}", file=sys.stderr)
        if e.code == 401:
            hint = (
                "Auth failed (401). If you're on OSS Airflow, enable BasicAuth in airflow.cfg:\n"
                "  api.auth_backend = airflow.api.auth.backend.basic_auth\n"
                "and supply AIRFLOW_USER / AIRFLOW_PASSWORD.\n"
                "Alternatively provide AIRFLOW_TOKEN if your deployment supports it."
            )
            print(hint, file=sys.stderr)
        raise
    except Exception as e:
        print(f"[REST] error: {e}", file=sys.stderr)
        raise


def trigger_via_cli(conf: dict) -> None:
    # Airflow コンテナ内 or PATHに `airflow` がある想定
    cmd = [
        "airflow",
        "dags",
        "trigger",
        DAG_ID,
        "--conf",
        json.dumps(conf, ensure_ascii=False),
    ]
    print(f"[CLI] $ {' '.join(cmd)}")
    subprocess.check_call(cmd)


def main() -> int:
    strategy_glob = os.getenv(
        "NOCTRIA_STRATEGY_GLOB", "src/strategies/veritas_generated/**.py"
    )
    extra_args = os.getenv("NOCTRIA_EXTRA_ARGS", "")
    conf = {
        "strategy_glob": strategy_glob,
        "extra_args": extra_args,
    }

    base_url = os.getenv("AIRFLOW_BASE_URL")
    token = os.getenv("AIRFLOW_TOKEN")
    user = os.getenv("AIRFLOW_USER")
    password = os.getenv("AIRFLOW_PASSWORD")

    # Prefer REST if base_url is provided (auth: Bearer > Basic > none)
    if base_url:
        try:
            print(
                "[INFO] Trying REST API "
                f"(base_url={base_url}, auth={'Bearer' if token else ('Basic' if user and password else 'none')})"
            )
            trigger_via_rest(base_url, conf, token=token, user=user, password=password)
            return 0
        except Exception:
            print("[WARN] REST failed. Falling back to CLI...", file=sys.stderr)

    # CLI fallback
    try:
        trigger_via_cli(conf)
        return 0
    except FileNotFoundError:
        print(
            "[ERROR] `airflow` command not found. Provide AIRFLOW_BASE_URL to use REST API, "
            "or ensure Airflow CLI is available in PATH.",
            file=sys.stderr,
        )
        return 2
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] airflow CLI failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
