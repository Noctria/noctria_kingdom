#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True)


def die(msg: str, cp: subprocess.CompletedProcess | None = None) -> None:
    if cp is not None:
        sys.stderr.write(cp.stderr)
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def git_changed_files(commit_range: str, path: str, find_renames: bool) -> List[str]:
    args = ["git", "diff", "--name-only", commit_range, "--", path]
    if find_renames:
        # -M は改名検出（rename detection）
        args.insert(2, "-M")
    cp = run(args)
    if cp.returncode != 0:
        die("git diff --name-only failed", cp)
    return [l.strip() for l in cp.stdout.splitlines() if l.strip()]


def git_diff_unified(commit_range: str, file_path: str, find_renames: bool) -> str:
    args = ["git", "diff", "-U2", commit_range, "--", file_path]
    if find_renames:
        args.insert(2, "-M")
    cp = run(args)
    if cp.returncode != 0:
        die(f"git diff for {file_path} failed", cp)
    return cp.stdout


def main():
    ap = argparse.ArgumentParser(description="Generate Markdown/JSON diff report for docs/")
    ap.add_argument("--range", default="HEAD~1..HEAD", help="git commit range, e.g. A..B (default: HEAD~1..HEAD)")
    ap.add_argument("--path", default="docs/", help="limit path (default: docs/)")
    ap.add_argument("--output", default="docs/_generated/diff_report.md", help="markdown report path")
    ap.add_argument("--json-sidecar", dest="json_sidecar", default=None, help="write JSON sidecar to this path")
    ap.add_argument("--summary-only", dest="summary_only", action="store_true", help="write only summary (no per-file diffs)")
    ap.add_argument("--find-renames", dest="find_renames", action="store_true", help="enable rename detection (-M)")
    args = ap.parse_args()

    # 出力ディレクトリ
    out_md = Path(args.output)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    if args.json_sidecar:
        Path(args.json_sidecar).parent.mkdir(parents=True, exist_ok=True)

    # 変更ファイル一覧
    changed = git_changed_files(args.range, args.path, args.find_renames)
    ts = dt.datetime.now().isoformat(timespec="seconds")

    # Markdown 出力
    with out_md.open("w", encoding="utf-8") as f:
        f.write(f"# Docs Diff Report\n\n- range: `{args.range}`\n- path: `{args.path}`\n- generated_at: {ts}\n\n")
        if not changed:
            f.write("_No changes in range._\n")
        else:
            f.write("## Changed files\n")
            for p in changed:
                f.write(f"- `{p}`\n")
            f.write("\n---\n")
            if not args.summary_only:
                for p in changed:
                    f.write(f"### `{p}`\n\n")
                    diff = git_diff_unified(args.range, p, args.find_renames)
                    if not diff.strip():
                        f.write("_(binary or no textual diff)_\n\n")
                        continue
                    f.write("```diff\n")
                    f.write(diff)
                    f.write("\n```\n\n")

    print(f"✅ Wrote {out_md}")

    # JSON sidecar（任意）
    if args.json_sidecar is not None:
        data: Dict[str, Any] = {
            "range": args.range,
            "path": args.path,
            "generated_at": ts,
            "changed_files": changed,
            "files": [],
            "summary_only": bool(args.summary_only),
            "find_renames": bool(args.find_renames),
        }
        if not args.summary_only:
            for p in changed:
                diff = git_diff_unified(args.range, p, args.find_renames)
                data["files"].append({"path": p, "diff": diff})
        Path(args.json_sidecar).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Wrote {args.json_sidecar}")


if __name__ == "__main__":
    main()
