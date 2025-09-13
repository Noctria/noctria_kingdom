#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_handoff.py

直近のコミットや進捗をまとめて handoff/ ディレクトリに Markdown(+JSON) を生成するスクリプト。
- --lookback-hours N : 直近N時間の更新を抽出（デフォルト24）
- --next-from FILE   : 次アクションを外部ファイル（.md/.txt）から読み込む（各行を1項目）
"""
from __future__ import annotations
from pathlib import Path
import argparse
import subprocess
import datetime as dt
import json
import os
import shlex

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = ROOT / "handoff"
HANDOFF_DIR.mkdir(exist_ok=True)

def run(cmd: str) -> str:
    return subprocess.check_output(shlex.split(cmd), text=True, cwd=str(ROOT)).strip()

def recent_commits(hours: int) -> list[dict]:
    since = (dt.datetime.now() - dt.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        # ハッシュ、サブジェクト、相対時刻、日時
        fmt = r"%h|%s|%cr|%cd"
        out = run(f'git log --since="{since}" --pretty=format:{fmt} --date=iso')
        lines = [ln for ln in out.splitlines() if ln.strip()]
    except subprocess.CalledProcessError:
        lines = []
    commits = []
    for ln in lines:
        parts = ln.split("|", 3)
        if len(parts) == 4:
            h, subj, rel, ts = parts
            commits.append({"hash": h, "title": subj, "when": rel, "timestamp": ts})
    return commits

def read_next_actions(path: str | None) -> list[str]:
    if not path:
        return [
            "DAG 本処理の組み込み",
            "戦略指定パラメータの対応",
            "結果の artifact / PR コメント出力",
        ]
    p = Path(path)
    if not p.exists():
        return [f"(next-from が見つかりません: {path})"]
    items = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip("-• ").strip()
        if ln:
            items.append(ln)
    return items or ["(次アクションが空)"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-hours", type=int, default=24)
    ap.add_argument("--next-from", type=str, default=None)
    args = ap.parse_args()

    now = dt.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_tag = now.date().isoformat()

    md_path = HANDOFF_DIR / f"handoff_{date_tag}.md"
    json_path = HANDOFF_DIR / f"handoff_{date_tag}.json"

    commits = recent_commits(args.lookback_hours)
    next_actions = read_next_actions(args.next_from)

    data = {
        "generated_at": now_str,
        "lookback_hours": args.lookback_hours,
        "commits": commits,
        "next_actions": next_actions,
    }

    # Markdown生成
    md = []
    md.append(f"# 📝 引き継ぎレポート ({now_str})")
    md.append(f"_直近 **{args.lookback_hours}h** の更新を集計_\n")
    md.append("## ✅ 最近のコミット")
    if not commits:
        md.append("- （該当なし）")
    else:
        for c in commits:
            md.append(f"- {c['hash']} {c['title']} ({c['when']})")
    md.append("\n## 🚩 次アクション")
    for a in next_actions:
        md.append(f"- [ ] {a}")

    # 機械可読（コメント貼付時も抽出できる）
    md.append("\n<!--HANDOFF_JSON")
    md.append(json.dumps(data, ensure_ascii=False))
    md.append("HANDOFF_JSON-->")

    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✅ Handoff written:\n- {md_path}\n- {json_path}")

if __name__ == "__main__":
    main()
