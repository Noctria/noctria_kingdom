# src/ai_cycle/cycle_logger.py
"""
AI開発サイクル（ターン）進捗記録用DBユーティリティ
Noctria Kingdom 共通モジュール
"""

import psycopg2
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# .envから接続情報を取得（未設定ならデフォルト値）
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "airflow")
DB_USER = os.getenv("DB_USER", "airflow")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password_here")  # ここは実際の環境値で上書き推奨

def insert_turn_history(
    turn_number: int,
    passed_tests: int,
    total_tests: int,
    generated_files: int,
    review_comments: int,
    failed: bool,
    fail_reason: str = None,
    extra_info: dict = None,
    finished_at: datetime = None
) -> int:
    """
    AIサイクル1ターンの進捗・品質情報をDBに記録
    :return: 新規登録レコードのid
    """
    pass_rate = round((passed_tests / total_tests) * 100, 2) if total_tests else 0.0

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        sql = """
        INSERT INTO ai_devcycle_turn_history
            (turn_number, started_at, finished_at, passed_tests, total_tests, pass_rate, generated_files, review_comments, failed, fail_reason, extra_info)
        VALUES
            (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        cur.execute(
            sql,
            (
                turn_number,
                finished_at or datetime.now(),
                passed_tests,
                total_tests,
                pass_rate,
                generated_files,
                review_comments,
                failed,
                fail_reason,
                json.dumps(extra_info or {}),
            ),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return new_id

    except Exception as e:
        print(f"[cycle_logger] DB記録エラー: {e}")
        return -1
