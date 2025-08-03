import re
import psycopg2
import json
from datetime import datetime

# === 設定（環境に応じて修正） ===
LOG_PATH = "generated_code/chat_log.txt"

DB_CONFIG = dict(
    dbname="airflow",
    user="airflow",
    password="airflow",   # ←ここを実際の値に
    host="localhost",          # or 'db' などDocker構成に応じて
    port=5432
)

# === パターン定義 ===
TURN_PATTERN = re.compile(r'ERROR collecting generated_code/(test_turn(\d+)\.py)')
ERR_TYPE_PATTERN = re.compile(r'(RequestException|AssertionError|NetworkError|Exception|ERROR)')

def parse_errors(log_path):
    """
    chat_log.txtからターンごとの失敗・KPI情報をパースしdictリストで返す
    """
    turn_stats = {}
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    current_turn = None
    for line in lines:
        turn_match = TURN_PATTERN.search(line)
        if turn_match:
            current_turn = int(turn_match.group(2))
            if current_turn not in turn_stats:
                turn_stats[current_turn] = {
                    "turn_number": current_turn,
                    "started_at": None,
                    "finished_at": None,
                    "passed_tests": 0,
                    "total_tests": 0,
                    "pass_rate": 0.0,
                    "generated_files": 1,
                    "review_comments": 0,
                    "failed": False,
                    "fail_reason": "",
                    "extra_info": {"fail_types": {}, "fail_count": 0},
                    "created_at": datetime.now()
                }
        err_types = ERR_TYPE_PATTERN.findall(line)
        if err_types and current_turn is not None:
            turn_stats[current_turn]["failed"] = True
            turn_stats[current_turn]["fail_reason"] = "; ".join(set(err_types))
            for t in err_types:
                turn_stats[current_turn]["extra_info"]["fail_types"][t] = \
                    turn_stats[current_turn]["extra_info"]["fail_types"].get(t, 0) + 1
                turn_stats[current_turn]["extra_info"]["fail_count"] += 1

    # 合格数・総数のダミー値。pytest等と連携したい場合はここを修正
    for t, row in turn_stats.items():
        row["total_tests"] = row["extra_info"]["fail_count"] or 1
        row["passed_tests"] = 0 if row["failed"] else row["total_tests"]
        row["pass_rate"] = 100.0 * row["passed_tests"] / row["total_tests"] if row["total_tests"] else 0.0
        # started_at, finished_atのダミー値（必要ならログから拾う or 未設定でOK）
        if row["started_at"] is None:
            row["started_at"] = datetime.now()
        if row["finished_at"] is None:
            row["finished_at"] = row["started_at"]
    return [v for _, v in sorted(turn_stats.items())]

def upsert_devcycle_turn(history_rows):
    """
    ai_devcycle_turn_history テーブルへUPSERT
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    for row in history_rows:
        cur.execute("""
            INSERT INTO ai_devcycle_turn_history
              (turn_number, started_at, finished_at, passed_tests, total_tests, pass_rate,
               generated_files, review_comments, failed, fail_reason, extra_info, created_at)
            VALUES
              (%(turn_number)s, %(started_at)s, %(finished_at)s, %(passed_tests)s, %(total_tests)s, %(pass_rate)s,
               %(generated_files)s, %(review_comments)s, %(failed)s, %(fail_reason)s, %(extra_info)s, %(created_at)s)
            ON CONFLICT (turn_number)
            DO UPDATE SET
                passed_tests=EXCLUDED.passed_tests,
                total_tests=EXCLUDED.total_tests,
                pass_rate=EXCLUDED.pass_rate,
                generated_files=EXCLUDED.generated_files,
                review_comments=EXCLUDED.review_comments,
                failed=EXCLUDED.failed,
                fail_reason=EXCLUDED.fail_reason,
                extra_info=EXCLUDED.extra_info,
                finished_at=EXCLUDED.finished_at,
                created_at=EXCLUDED.created_at
        """, {
            "turn_number": row["turn_number"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "passed_tests": row["passed_tests"],
            "total_tests": row["total_tests"],
            "pass_rate": row["pass_rate"],
            "generated_files": row["generated_files"],
            "review_comments": row["review_comments"],
            "failed": row["failed"],
            "fail_reason": row["fail_reason"],
            "extra_info": json.dumps(row["extra_info"], ensure_ascii=False),
            "created_at": row["created_at"],
        })
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("Parsing log and upserting turn KPI to Postgres...")
    history = parse_errors(LOG_PATH)
    upsert_devcycle_turn(history)
    print(f"Upserted {len(history)} turns into ai_devcycle_turn_history.")
