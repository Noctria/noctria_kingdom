#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, datetime as dt, subprocess, sys
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        print("ERROR:", " ".join(cmd), r.stderr.strip(), file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout

def main():
    ap = argparse.ArgumentParser(description="Generate Markdown diff report for docs/")
    ap.add_argument("--range", default="HEAD~1..HEAD", help="git commit range, e.g. A..B (default: HEAD~1..HEAD)")
    ap.add_argument("--output", default="docs/_generated/diff_report.md")
    ap.add_argument("--path", default="docs/", help="limit path (default: docs/)")
    args = ap.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # 変更ファイル一覧
    changed = run(["git","diff","--name-only",args.range,"--",args.path]).strip().splitlines()
    ts = dt.datetime.now().isoformat(timespec="seconds")
    with open(args.output,"w",encoding="utf-8") as f:
        f.write(f"# Docs Diff Report\n\n- range: `{args.range}`\n- path: `{args.path}`\n- generated_at: {ts}\n\n")
        if not changed:
            f.write("_No changes in range._\n")
            return
        f.write("## Changed files\n")
        for p in changed:
            f.write(f"- `{p}`\n")
        f.write("\n---\n")

        # 各ファイルの差分をdiffフェンスで埋め込む
        for p in changed:
            f.write(f"### `{p}`\n\n")
            diff = run(["git","diff","-U2", args.range, "--", p])
            if not diff.strip():
                f.write("_(binary or no textual diff)_\n\n")
                continue
            f.write("```diff\n")
            f.write(diff)
            f.write("\n```\n\n")

    print(f"✅ Wrote {args.output}")

if __name__ == "__main__":
    main()
