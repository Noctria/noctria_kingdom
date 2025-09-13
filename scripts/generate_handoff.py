#!/usr/bin/env python3
"""
scripts/generate_handoff.py

直近のコミットや進捗をまとめて handoff/ ディレクトリに Markdown を生成するスクリプト。
"""

from pathlib import Path
import subprocess
import datetime

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = ROOT / "handoff"
HANDOFF_DIR.mkdir(exist_ok=True)

def get_recent_commits(n=5):
    try:
        out = subprocess.check_output(
            ["git", "log", f"-{n}", "--pretty=format:%h %s (%cr)"],
            text=True
        )
        return out.strip().splitlines()
    except Exception as e:
        return [f"(コミット取得エラー: {e})"]

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = HANDOFF_DIR / f"handoff_{datetime.date.today().isoformat()}.md"

    commits = get_recent_commits(10)

    content = []
    content.append(f"# 📝 引き継ぎレポート ({now})\n")
    content.append("## ✅ 最近のコミット\n")
    for c in commits:
        content.append(f"- {c}")
    content.append("\n## 🔄 次アクション（例）\n")
    content.append("- [ ] DAG 本処理の組み込み")
    content.append("- [ ] 戦略指定パラメータの対応")
    content.append("- [ ] 結果の artifact / PR コメント出力\n")

    filename.write_text("\n".join(content), encoding="utf-8")
    print(f"✅ Handoff report generated: {filename}")

if __name__ == "__main__":
    main()
