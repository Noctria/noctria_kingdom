import optuna
from optuna.storages import RDBStorage

# === 設定 ===
sqlite_path = "/opt/airflow/data/optuna_study.db"
postgres_url = "postgresql+psycopg2://airflow:airflow@postgres:5432/optuna_db"
study_name = "my_study"  # SQLiteで使っていたStudy名

# === SQLiteから既存Studyを読み込み ===
print(f"📥 SQLiteからStudyを読み込み中: {sqlite_path}")
sqlite_storage = RDBStorage(f"sqlite:///{sqlite_path}")
study = optuna.load_study(study_name=study_name, storage=sqlite_storage)

# === PostgreSQL用ストレージ定義 ===
pg_storage = RDBStorage(postgres_url)

# === PostgreSQLにStudyを作成（存在チェック） ===
try:
    optuna.create_study(
        study_name=study_name,
        storage=pg_storage,
        direction=study.direction
    )
    print(f"✅ PostgreSQLに新Study作成: {study_name}")
except optuna.exceptions.DuplicatedStudyError:
    print(f"⚠️ PostgreSQLに既にStudyが存在: {study_name}")

# === 全Trialを移行（enqueue） ===
print(f"🚚 TrialをPostgreSQLに移行中...")
for trial in study.trials:
    if trial.state.is_finished():
        new_study = optuna.load_study(study_name=study_name, storage=pg_storage)
        new_study.enqueue_trial(trial.params)

print("✅ StudyとTrialの移行が完了しました！")
