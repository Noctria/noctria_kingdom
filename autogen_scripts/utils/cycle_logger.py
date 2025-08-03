import psycopg2
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "airflow")
DB_USER = os.getenv("DB_USER", "airflow")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not DB_PASSWORD or DB_PASSWORD == "your_password_here":
    raise RuntimeError("DB_PASSWORD が設定されていません。環境変数を確認してください。")

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
    pass_rate = round((passed_tests / total_tests) * 100, 2) if total_tests else 0.0

    conn = None
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
        return new_id

    except Exception as e:
        print(f"[cycle_logger] DB記録エラー: {e}")
        return -1

    finally:
        if conn:
            conn.close()
