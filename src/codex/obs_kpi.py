# src/codex/obs_kpi.py
from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import Json

from src.core.envload import load_noctria_env


def log_kpi(agent: str, metric: str, value: float | None, detail: dict | None = None) -> None:
    load_noctria_env()
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:  # ないときは黙ってスキップ（ローカルでも壊れない）
        return
    with psycopg2.connect(dsn) as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO obs_codex_kpi(agent, metric, value, detail) VALUES (%s,%s,%s,%s)",
            (agent, metric, value, Json(detail or {})),
        )
