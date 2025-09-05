# tools/generate_readme_summary.py

import subprocess

README_PATH = "README_latest.md"

with open(README_PATH, "w") as f:
    f.write("# 📘 Noctria Kingdom 最新構成 (tree -L 3)\n\n")
    f.write("```bash\n")
    subprocess.run(["tree", "-L", "3"], stdout=f)
    f.write("```\n")
    f.write("\n## 🗂 各フォルダ概要\n")
    f.write("- `airflow_docker/`: Airflow本体・DAG群・Docker設定\n")
    f.write("- `execution/`: 実行・発注・監視ロジック群\n")
    f.write("- `experts/`: MQL5形式のEA戦略群\n")
    f.write("- `veritas/`: 戦略生成AIモジュール\n")
    f.write("- `llm_server/`: FastAPI経由のローカル推論サーバー\n")
    f.write("- `tools/`: 各種ツール・リファクタスクリプト\n")
    f.write("- `tests/`: ユニット・統合・ストレステスト群\n")
    f.write("- `docs/`: README、構成説明、セットアップ手順など\n")
    f.write("- `logs/`: 監査・評価ログ\n")

print(f"✅ README生成完了: {README_PATH}")
