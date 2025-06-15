from pathlib import Path
from tabulate import tabulate

VOLUME_MAP = {
    "data": "/opt/airflow/data",
    "core": "/opt/noctria/core",
    "strategies": "/opt/noctria/strategies",
    "scripts": "/opt/noctria/scripts",
    "logs": "/opt/airflow/logs"
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # ← scripts/ から1階層戻る
mapping = []

for path in PROJECT_ROOT.rglob("*"):
    if path.is_file():
        rel_path = path.relative_to(PROJECT_ROOT)
        if len(rel_path.parts) == 0:
            continue
        top_dir = rel_path.parts[0]
        if top_dir in VOLUME_MAP:
            container_path = Path(VOLUME_MAP[top_dir]) / Path(*rel_path.parts[1:])
            mapping.append([
                str(rel_path),
                str(path),
                str(container_path)
            ])

if mapping:
    print(tabulate(mapping, headers=["📁 Git相対パス", "💻 WSLパス", "📦 Docker内パス"]))
else:
    print("⚠️ 一致するファイルが見つかりませんでした。VOLUME_MAPとファイル構成をご確認ください。")
