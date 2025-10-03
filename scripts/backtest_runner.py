#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight Backtest Runner (no heavy deps)

目的:
- GPU/重依存なしで「とりあえず全戦略を走らせて結果を一覧化」する軽量ランナー
- DAG/Actions から artifact として JSON/CSV/HTML を収集できるように整形出力

主な仕様:
- グロブで戦略を収集（複数 --pattern 可 / 環境変数 NOCTRIA_STRATEGY_GLOB でも上書き可）
- 0件でも安全に完走（空リストを出力）
- 各戦略についてダミースコアを生成（将来ここを本物のBTに差し替え）
- outdir に result.json / result.csv / report.html / summary.txt を出力
- 追加引数文字列は --extra-args or NOCTRIA_EXTRA_ARGS から受け取って記録だけ行う
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import os
import random
import sys
from datetime import datetime
from typing import Iterable, List


# ---------- CLI / ENV 取り回し ----------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Lightweight backtest runner (no heavy deps).")
    p.add_argument(
        "--pattern",
        action="append",
        help="戦略ファイルのグロブ。複数指定可。未指定時はデフォルト or 環境変数を利用。",
    )
    p.add_argument("--extra-args", default="", help="追加引数（記録のみ）")
    p.add_argument("--outdir", required=True, help="成果物出力先ディレクトリ")
    p.add_argument("--limit", type=int, default=0, help="テスト件数の上限(0なら無制限)")
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="除外グロブ（例: tests/**、_graveyard/**）。複数指定可",
    )
    p.add_argument("--seed", type=int, default=0, help="固定シード（0なら各戦略名ハッシュに依存）")
    return p.parse_args()


def resolve_patterns(cli_patterns: List[str] | None) -> List[str]:
    """
    パターン解決の優先度:
      1) CLI の --pattern (複数可)
      2) 環境変数 NOCTRIA_STRATEGY_GLOB (カンマ区切り可)
      3) デフォルト: src/strategies/veritas_generated/**.py
    """
    if cli_patterns:
        return cli_patterns

    env = os.getenv("NOCTRIA_STRATEGY_GLOB", "").strip()
    if env:
        # カンマ/空白区切り許容
        parts = [s for s in (x.strip() for x in env.replace(",", " ").split()) if s]
        if parts:
            return parts

    return ["src/strategies/veritas_generated/**.py"]


def ensure_dir(p: str) -> str:
    os.makedirs(p, exist_ok=True)
    return p


# ---------- ダミー計算 ----------
def fake_score(seed: int) -> dict:
    rnd = random.Random(seed)
    return {
        "win_rate": round(rnd.uniform(0.35, 0.75), 4),
        "profit_factor": round(rnd.uniform(0.8, 2.5), 3),
        "sharpe": round(rnd.uniform(-0.2, 1.8), 3),
        "trades": rnd.randint(20, 300),
    }


# ---------- ユーティリティ ----------
def list_files_by_patterns(patterns: Iterable[str], excludes: Iterable[str]) -> List[str]:
    """patterns を再帰展開し excludes で除外したパスを返す"""
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat, recursive=True))
    if excludes:
        excluded: set[str] = set()
        for ex in excludes:
            excluded.update(glob.glob(ex, recursive=True))
        files = [f for f in files if f not in excluded]
    # ファイルのみ & 重複排除 & ソート
    uniq = sorted({f for f in files if os.path.isfile(f)})
    return uniq


def stable_seed_for(name: str, base_seed: int = 0) -> int:
    """ファイル名から安定seedを得る（base_seed が0以外ならそれも加味）"""
    h = hash(name) & 0xFFFFFFFF
    if base_seed:
        h ^= base_seed & 0xFFFFFFFF
    return h & 0xFFFF


# ---------- メイン ----------
def main() -> int:
    args = parse_args()
    outdir = ensure_dir(args.outdir)

    # パターン解決（CLI/ENV/デフォルト）
    patterns = resolve_patterns(args.pattern)
    extra_args = os.getenv("NOCTRIA_EXTRA_ARGS", args.extra_args)

    started_at = datetime.utcnow().isoformat()

    # 戦略列挙
    files = list_files_by_patterns(patterns, args.exclude)
    if args.limit and len(files) > args.limit:
        files = files[: args.limit]

    results = []
    for path in files:
        # リポジトリ相対表記（artifactで見やすくする）
        try:
            name = os.path.relpath(path, start=os.getcwd())
        except Exception:
            name = path

        # ※ 将来ここで本物のBT（バックテスト）を呼び出す
        s = fake_score(stable_seed_for(name, args.seed))
        results.append({"strategy": name, **s})

    # JSON
    summary = {
        "ok": True,
        "mode": "lightweight",
        "patterns": patterns,
        "extra_args": extra_args,
        "started_at": started_at,
        "finished_at": datetime.utcnow().isoformat(),
        "count": len(results),
        "top3_by_pf": sorted(results, key=lambda r: r["profit_factor"], reverse=True)[:3]
        if results
        else [],
        "results": results,
    }
    with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # CSV
    csv_path = os.path.join(outdir, "result.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write("strategy,win_rate,profit_factor,sharpe,trades\n")
        for r in results:
            f.write(
                f"{r['strategy']},{r['win_rate']},{r['profit_factor']},{r['sharpe']},{r['trades']}\n"
            )

    # HTML（ざっくりテーブル）
    html_rows = "\n".join(
        (
            "<tr>"
            f"<td>{html.escape(r['strategy'])}</td>"
            f"<td>{r['win_rate']}</td>"
            f"<td>{r['profit_factor']}</td>"
            f"<td>{r['sharpe']}</td>"
            f"<td>{r['trades']}</td>"
            "</tr>"
        )
        for r in results
    )
    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Noctria Backtest Report</title>
  <style>
    body{{font-family:sans-serif;margin:20px}}
    table{{border-collapse:collapse;margin-top:10px}}
    td,th{{border:1px solid #999;padding:4px 8px}}
    code{{background:#f4f4f4;padding:2px 4px;border-radius:4px}}
  </style>
</head>
<body>
  <h1>Noctria Backtest Report</h1>
  <p>patterns: {", ".join(f"<code>{html.escape(p)}</code>" for p in patterns)}</p>
  <p>extra_args: <code>{html.escape(extra_args)}</code></p>
  <p>count: {len(results)}</p>
  <table>
    <thead>
      <tr><th>strategy</th><th>win_rate</th><th>profit_factor</th><th>sharpe</th><th>trades</th></tr>
    </thead>
    <tbody>
      {html_rows or "<tr><td colspan='5'>(no strategies matched)</td></tr>"}
    </tbody>
  </table>
</body>
</html>"""
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as f:
        f.write(html_doc)

    # サマリ（Actionsログなどでチラ見用）
    with open(os.path.join(outdir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(
            "Noctria lightweight backtest summary\n"
            f"- patterns: {patterns}\n"
            f"- extra_args: {extra_args}\n"
            f"- count: {len(results)}\n"
            f"- started_at: {started_at}\n"
            f"- finished_at: {datetime.utcnow().isoformat()}\n"
        )

    print(f"[runner] wrote: {outdir}/result.json, result.csv, report.html, summary.txt")
    print(f"[runner] strategies matched: {len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
