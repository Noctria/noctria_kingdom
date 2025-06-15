from pathlib import Path
from tabulate import tabulate

# ✅ 各ホスト側ディレクトリと、対応するDocker内パスのマッピング辞書
VOLUME_MAP = {
    "data": "/opt/airflow/data",
    "core": "/opt/noctria/core",
    "strategies": "/opt/noctria/strategies",
    "scripts": "/opt/noctria/scripts",
    "logs": "/opt/airflow/logs"
}

# ✅ プロジェクトのルート（このスクリプトを置く場所）
PROJECT_ROOT = Path(__file__).resolve().parent

# マッピングリスト
mapping = []

for path in PROJECT_ROOT.rglob("*.*"):
    try:
        rel_path = path.relative_to(PROJECT_ROOT)
    except ValueError:
        continue

    top_dir = rel_path.parts[0]
    if top_dir in VOLUME_MAP:
        container_path = Path(VOLUME_MAP[top_dir]) / Path(*rel_path.parts[1:])
        mapping.append([
            str(rel_path),     # 📁 Git相対パス
            str(path),         # 💻 WSL絶対パス
            str(container_path)  # 📦 Dockerパス
        ])

# ✅ 表として表示
print(tabulate(mapping, headers=["📁 Git相対パス", "💻 WSLパス", "📦 Docker内パス"]))
