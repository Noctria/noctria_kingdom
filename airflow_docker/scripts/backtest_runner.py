#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight Backtest Runner (no heavy deps)
- グロブで戦略を収集
- 各戦略について簡易スコアを生成（ダミー）
- outdir に JSON/CSV/HTML を出力
"""
from __future__ import annotations
import argparse, json, os, sys, glob, time, random, html
from datetime import datetime

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pattern", default="src/strategies/veritas_generated/**.py")
    p.add_argument("--extra-args", default="")
    p.add_argument("--outdir", required=True)
    return p.parse_args()

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)
    return p

def fake_score(seed: int) -> dict:
    rnd = random.Random(seed)
    return {
        "win_rate": round(rnd.uniform(0.35, 0.75), 4),
        "profit_factor": round(rnd.uniform(0.8, 2.5), 3),
        "sharpe": round(rnd.uniform(-0.2, 1.8), 3),
        "trades": rnd.randint(20, 300),
    }

def main():
    args = parse_args()
    outdir = ensure_dir(args.outdir)
    started_at = datetime.utcnow().isoformat()

    # 戦略列挙
    files = sorted(glob.glob(args.pattern, recursive=True))
    results = []
    for i, path in enumerate(files):
        name = os.path.relpath(path, start=os.getcwd())
        # 本来はここで本物のBTを実行する
        time.sleep(0.02)  # 擬似的な処理時間
        s = fake_score(hash(name) & 0xffff)
        results.append({"strategy": name, **s})

    # JSON
    summary = {
        "ok": True,
        "mode": "lightweight",
        "pattern": args.pattern,
        "extra_args": args.extra_args,
        "started_at": started_at,
        "finished_at": datetime.utcnow().isoformat(),
        "count": len(results),
        "top3_by_pf": sorted(results, key=lambda r: r["profit_factor"], reverse=True)[:3],
        "results": results,
    }
    with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # CSV
    csv_path = os.path.join(outdir, "result.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("strategy,win_rate,profit_factor,sharpe,trades\n")
        for r in results:
            f.write(f"{r['strategy']},{r['win_rate']},{r['profit_factor']},{r['sharpe']},{r['trades']}\n")

    # HTML（ざっくりテーブル）
    html_rows = "\n".join(
        f"<tr><td>{html.escape(r['strategy'])}</td>"
        f"<td>{r['win_rate']}</td><td>{r['profit_factor']}</td>"
        f"<td>{r['sharpe']}</td><td>{r['trades']}</td></tr>"
        for r in results
    )
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Noctria Backtest Report</title>
<style>body{{font-family:sans-serif}}table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:4px 8px}}</style>
</head><body>
<h1>Noctria Backtest Report</h1>
<p>pattern: <code>{html.escape(args.pattern)}</code></p>
<p>extra_args: <code>{html.escape(args.extra_args)}</code></p>
<p>count: {len(results)}</p>
<table><thead><tr><th>strategy</th><th>win_rate</th><th>profit_factor</th><th>sharpe</th><th>trades</th></tr></thead>
<tbody>{html_rows}</tbody></table>
</body></html>"""
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"[runner] wrote: {outdir}/result.json, result.csv, report.html")
    return 0

if __name__ == "__main__":
    sys.exit(main())
