#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, sys
from pathlib import Path

def load_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data

def normalize_changed_files(data: dict):
    """
    サポートする入力フォーマット:
    A) 新: { changed_files: [..], files: [...], summary_only: bool, ... }
    B) 旧: { changes: [ {path:..., diff:...}, ...] }
    """
    # A) 新スキーマ
    if "changed_files" in data:
        files = list(map(str, data.get("changed_files") or []))
        # files 詳細があるなら優先的に使えるよう返す
        details = data.get("files") or []
        return files, details

    # B) 旧スキーマ
    if "changes" in data and isinstance(data["changes"], list):
        files = [str(x.get("path")) for x in data["changes"] if x.get("path")]
        details = data["changes"]
        return files, details

    # どちらも無い場合は空集合で返す（エラーにしない）
    return [], []

def main():
    ap = argparse.ArgumentParser(description="Weekly paste snippet generator")
    ap.add_argument("--json", required=True, help="diff_report.json path")
    ap.add_argument("--out", default="docs/_generated/weekly_insert.md", help="output snippet path")
    ap.add_argument("--title", default="Weekly Paste Snippet")
    args = ap.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"ERROR: not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    data = load_json(json_path)
    changed_files, details = normalize_changed_files(data)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # メタ情報
    rng = data.get("range", "")
    ts  = data.get("generated_at", "")
    summary_only = bool(data.get("summary_only", False))

    # 簡易スニペット
    lines = []
    lines.append(f"# {args.title}")
    lines.append("")
    meta = []
    if rng: meta.append(f"range: `{rng}`")
    if ts:  meta.append(f"generated_at: {ts}")
    if meta:
        lines.append("- " + "\n- ".join(meta))
        lines.append("")
    lines.append(f"## Changed files ({len(changed_files)})")
    if changed_files:
        lines.extend([f"- `{p}`" for p in changed_files])
    else:
        lines.append("_No changes detected._")
    lines.append("")

    # 詳細（summary_only でない＆details があれば）
    if not summary_only and details:
        lines.append("---")
        for it in details:
            p = it.get("path","(unknown)")
            diff = it.get("diff","")
            lines.append(f"### `{p}`")
            lines.append("")
            if diff.strip():
                lines.append("```diff")
                lines.append(diff)
                lines.append("```")
            else:
                lines.append("_(no textual diff)_")
            lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Wrote {out_path}")

if __name__ == "__main__":
    main()
