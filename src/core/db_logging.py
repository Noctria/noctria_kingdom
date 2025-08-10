# src/core/db_logging.py
import os
import psycopg2
from datetime import datetime
from typing import Optional, Dict, Any

def log_event(
    table: str,
    event_type: str,
    payload: Dict[str, Any],
    occurred_at: Optional[datetime] = None
):
    """
    任意のイベントテーブルにログを記録する共通関数

    :param table: テーブル名 (例: validation_events)
    :param event_type: イベント種別 (例: 'PLAN_CHECK', 'RISK_ALERT')
    :param payload: JSON化して保存する詳細データ
    :param occurred_at: 発生日時 (省略時は現在時刻)
    """
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "airflow"),
        user=os.getenv("POSTGRES_USER", "airflow"),
        password=os.getenv("POSTGRES_PASSWORD", "airflow"),
        host=os.getenv("POSTGRES_HOST", "noctria_postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )
    cur = conn.cursor()

    cur.execute(f"""
        INSERT INTO {table} (event_type, payload, occurred_at)
        VALUES (%s, %s, %s)
    """, (event_type, json.dumps(payload, ensure_ascii=False), occurred_at or datetime.utcnow()))

    conn.commit()
    cur.close()
    conn.close()
