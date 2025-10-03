# tools/graph_prune_apply.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graph_prune_apply.py
- REMOVE候補(ID)とMERGE候補(ファイルパス)から、"実行前提の下書きbash"を生成
- デフォルトは --dry-run でコメント行中心の安全設計
- 実行は人間レビュー後に、必要行のコメントを外して個別に実施推奨

使い方:
  python3 tools/graph_prune_apply.py \
    --project-root /mnt/d/noctria_kingdom \
    --remove-list viz/remove_candidates.txt \
    --merge-list viz/merge_candidates.txt \
    --dry-run \
    --bash-out viz/prune_apply.sh
"""
from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
from typing import Dict, List

def guess_paths_from_ids(ids: List[str], project_root: str) -> Dict[str, str]:
    # 簡易逆引き: "src_a_b_py" → src/a/b.py や src/a/b/__init__.py を試す
    out = {}
    for nid in ids:
        base = re.sub(r"_", "/", nid)  # "src/a/b/py"
        candidates = []
        if base.endswith("/py"):
            candidates.append(base[:-3] + ".py")
        # よくある拡張も少しだけ
        for ext in [".py", ".html", ".js", ".md", ".yaml", ".yml", ".toml"]:
            if not base.endswith(ext):
                candidates.append(base + ext)
        # 探索
        found = ""
        for c in candidates:
            p = Path(project_root)/c
            if p.exists():
                found = str(p)
                break
        out[nid] = found  # 空なら未解決
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--remove-list", required=True, type=Path)
    ap.add_argument("--merge-list", required=True, type=Path)
    ap.add_argument("--bash-out", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    remove_ids = [s.strip() for s in args.remove_list.read_text(encoding="utf-8").splitlines() if s.strip()]
    merge_files = [s.strip() for s in args.merge_list.read_text(encoding="utf-8").splitlines() if s.strip()]

    id2path = guess_paths_from_ids(remove_ids, args.project_root)

    lines = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail")
    lines.append("")
    lines.append("# === PRUNE APPLY (DRAFT) ===")
    lines.append(f"ROOT='{args.project_root}'")
    lines.append("")
    lines.append("echo '[INFO] This is a draft script. Review before execution.'")
    lines.append("")

    lines.append("# --- REMOVE candidates ----------------------------------------")
    for nid in remove_ids:
        p = id2path.get(nid) or ""
        if not p:
            lines.append(f"# [SKIP] unresolved path for ID: {nid}")
            continue
        # コメントアウトで提案（安全第一）
        lines.append(f"# rm -f '{p}'  # from ID: {nid}")

    lines.append("")
    lines.append("# --- MERGE candidates (suggested to consolidate) --------------")
    for p in merge_files:
        # ここでは削除せず、合併の提案だけ
        lines.append(f"# [MERGE] consider consolidating: '{p}' into a parent module")

    lines.append("")
    lines.append("echo '[INFO] Draft complete. Uncomment the lines you want to execute.'")
    args.bash_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 実行権限は必要に応じて
    try:
        os.chmod(args.bash_out, 0o755)
    except Exception:
        pass

if __name__ == "__main__":
    main()
