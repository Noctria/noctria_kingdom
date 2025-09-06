# codex/tools/collect_failures.py
from __future__ import annotations
import json, sys
from pathlib import Path
from typing import List, Dict

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m codex.tools.collect_failures <json_path> <out_md>")
        sys.exit(0)

    jpath = Path(sys.argv[1])
    out_md = Path(sys.argv[2])

    if not jpath.exists():
        out_md.write_text("# Patch Notes\n(no report found)\n")
        return

    data = json.loads(jpath.read_text())
    tests: List[Dict] = data.get("tests", [])
    failed = [t for t in tests if t.get("outcome") == "failed"]

    lines = ["# Patch Notes", ""]
    if not failed:
        lines.append("No failures. Nothing to patch 🎉")
    else:
        lines.append(f"{len(failed)} failures detected. Drafting notes:\n")
        for i, t in enumerate(failed, 1):
            nodeid = t.get("nodeid","")
            longrepr = t.get("longrepr","") or t.get("calllongrepr","")
            # 短くトリミング
            snippet = str(longrepr)
            if len(snippet) > 1200:
                snippet = snippet[:1200] + "\n... (truncated)\n"

            lines += [
                f"## {i}. {nodeid}",
                "",
                "### Failure Snippet",
                "```",
                snippet,
                "```",
                "### Suggested Fix (TODO by Inventor Scriptus)",
                "- Root cause hypothesis: _TODO_",
                "- File(s) likely affected: _TODO_",
                "- Proposed patch outline: _TODO_",
                "",
            ]

        # 最後にHarmonia向けチェックリスト
        lines += [
            "---",
            "## Reviewer (Harmonia Ordinis) Checklist",
            "- [ ] 変更がガードレールに適合（安全・可観測・再現性）",
            "- [ ] テストのカバレッジは十分",
            "- [ ] リグレッションがないことを LIGHT/必要に応じてFULL で確認",
        ]

    out_md.write_text("\n".join(lines))

if __name__ == "__main__":
    main()
