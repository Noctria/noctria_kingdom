# src/core/db_logging.py
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import psycopg2
import psycopg2.extras

# 軽量ロガー（setup_loggerは使わない）
_logger = logging.getLogger("db_logging")
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

def _get_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "airflow"),
        user=os.getenv("POSTGRES_USER", "airflow"),
        password=os.getenv("POSTGRES_PASSWORD", "airflow"),
        host=os.getenv("POSTGRES_HOST", "noctria_postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
    )

def log_event(
    table: str,
    event_type: str,
    payload: Dict[str, Any],
    occurred_at: Optional[datetime] = None,
) -> None:
    """
    任意のイベントテーブルへログを記録する軽量関数。
    期待スキーマ（例: pdca_events）:
      - event_type (text/varchar)
      - payload (jsonb)
      - occurred_at (timestamptz)
    """
    occurred_at = occurred_at or datetime.utcnow()
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            f"""INSERT INTO {table} (event_type, payload, occurred_at)
                VALUES (%s, %s, %s)""",
            (event_type, json.dumps(payload, ensure_ascii=False), occurred_at),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # ログだけ出して処理は落とさない（AirflowのDAG読み込み阻害を避ける）
        _logger.debug(f"[db_logging] failed to insert into {table}: {e}")
