#!/usr/bin/env python3
# coding: utf-8
"""
scripts/gen_governance_prompt.py

Noctria Kingdom 統治プロンプト完全版 生成スクリプト
"""

import datetime as dt
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "docs" / "_generated"
RULES_DIR = ROOT / "docs" / "rules" / "fintokei"

GENERATED.mkdir(parents=True, exist_ok=True)
RULES_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT = GENERATED / "governance_prompt_full.md"
TREE_SNAPSHOT = GENERATED / "tree_snapshot.txt"


def read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"# ⚠️ missing: {path}"


def fenced_block(content: str, lang: str = "text") -> str:
    """コードブロックでラップし、内部を安全にインデント"""
    return f"```{lang}\n{textwrap.dedent(content).rstrip()}\n```"


def build_tree_snapshot() -> str:
    try:
        tree = subprocess.check_output(
            ["tree", "-L", "3"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        )
        TREE_SNAPSHOT.write_text(tree, encoding="utf-8")
        return fenced_block(tree, "text")
    except Exception as e:
        return f"(tree コマンド取得失敗: {e})"


def main():
    timestamp = dt.datetime.now().isoformat()

    codex_main = read_file(ROOT / "docs/codex/Codex_Noctria.md")
    codex_agents = read_file(ROOT / "docs/codex/Codex_Noctria_Agents.md")
    king_code = read_file(ROOT / "src/core/king_noctria.py")

    # Fintokeiルール
    rules_texts = []
    for f in sorted(RULES_DIR.glob("*.md")):
        rules_texts.append(f"## {f.name}\n\n" + read_file(f))
    fintokei_rules = "\n\n---\n\n".join(rules_texts) if rules_texts else "⚠️ ルール未整備"

    tree_block = build_tree_snapshot()

    content = f"""# Noctria Kingdom 統治プロンプト完全版

生成日時: {timestamp}

---

## 📘 Codex 本編

{codex_main}

---

## 🧩 Codex Agents 定義

{codex_agents}

---

## 👑 King Noctria 定義

{fenced_block(king_code, "python")}

---

## 📜 Fintokei ルール要約

{fintokei_rules}

---

## 📂 プロジェクトツリー構造 (最新 snapshot)

{tree_block}
"""

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"✅ 統治プロンプト完全版を生成しました: {OUTPUT}")


if __name__ == "__main__":
    main()
