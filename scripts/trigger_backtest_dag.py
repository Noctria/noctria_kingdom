#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trigger noctria_backtest_dag via Airflow REST API (preferred) or CLI fallback.

Env (any of the following auth styles work):

# Base URL (required for REST)
  AIRFLOW_BASE_URL       e.g. http://localhost:8080

# Bearer token auth (if available; takes priority over Basic)
  AIRFLOW_TOKEN          e.g. eyJhbGciOi...

# Basic auth (typical on OSS Airflow with basic_auth backend)
  AIRFLOW_USER           e.g. admin
  AIRFLOW_PASSWORD       e.g. admin

# Optional conf to pass to DAG
  NOCTRIA_STRATEGY_GLOB  default: src/strategies/veritas_generated/**.py
  NOCTRIA_EXTRA_ARGS     default: ""

If REST fails (or AIRFLOW_BASE_URL is not set), try `airflow dags trigger` via CLI.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib import request, error

DAG_ID = "noctria_backtest_dag"
DEFAULT_TIMEOUT = 20  # seconds
BACKOFF_DELAYS = [0, 1, 2, 4]  # seconds


def _auth_header(token: Optional[str], user: Optional[str], password: Optional[str]) -> Optional[str]:
    """Return Authorization header value (Bearer > Basic) or None."""
    if token:
        return f"Bearer {token}"
    if user and password:
        b = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        return f"Basic {b}"
    return None


def _post_json(url: str, payload: Dict[str, Any], auth_header: Optional[str], timeout: float) -> str:
    req = request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if auth_header:
        req.add_header("Authorization", auth_header)
    with request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def trigger_via_rest(
    base_url: str,
    conf: dict,
    token: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Returns raw response body (JSON string). Raises on failure.
    """
    url = f"{base_url.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns"
    dag_run_id = f"manual__{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    payload = {"dag_run_id": dag_run_id, "conf": conf}
    auth_header = _auth_header(token, user, password)

    print(f"[INFO] Trying REST API (base_url={base_url}, auth={'Bearer' if token else ('Basic' if user and password else 'none')})")
    last_exc: Optional[Exception] = None
    for i, delay in enumerate(BACKOFF_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            body = _post_json(url, payload, auth_header, timeout=timeout)
            print("[REST] status=200")
            print(body)
            return body
        except error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")
            print(f"[REST] HTTPError {e.code}: {msg}", file=sys.stderr)
            if e.code == 401:
                print(
                    "HINT: For OSS Airflow enable BasicAuth:\n"
                    "  api.auth_backend = airflow.api.auth.backend.basic_auth\n"
                    "and provide AIRFLOW_USER / AIRFLOW_PASSWORD, or set AIRFLOW_TOKEN if supported.",
                    file=sys.stderr,
                )
            last_exc = e
        except Exception as e:
            print(f"[REST] error: {e}", file=sys.stderr)
            last_exc = e
    raise RuntimeError("Failed to trigger DAG via REST after retries") from last_exc


def trigger_via_cli(conf: dict) -> None:
    """
    Fallback to Airflow CLI in the current host/container.
    """
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
    strategy_glob = os.getenv("NOCTRIA_STRATEGY_GLOB", "src/strategies/veritas_generated/**.py")
    extra_args = os.getenv("NOCTRIA_EXTRA_ARGS", "")
    conf = {"strategy_glob": strategy_glob, "extra_args": extra_args}

    base_url = os.getenv("AIRFLOW_BASE_URL")
    token = os.getenv("AIRFLOW_TOKEN")
    user = os.getenv("AIRFLOW_USER")
    password = os.getenv("AIRFLOW_PASSWORD")

    if base_url:
        try:
            body = trigger_via_rest(base_url, conf, token=token, user=user, password=password)
            # best-effort: print DAG_RUN_ID=... (helps shell capture)
            try:
                data = json.loads(body)
                dag_run_id = data.get("dag_run_id") or data.get("dagRunId")
                if dag_run_id:
                    print(f"DAG_RUN_ID={dag_run_id}")
            except Exception:
                pass
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
