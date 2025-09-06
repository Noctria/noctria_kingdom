# codex/tools/patch_gen.py
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Iterable, Tuple

from codex.agents.inventor import InventorOutput, PatchSuggestion

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "codex_reports"
PATCHES_DIR = REPORTS_DIR / "patches"
PATCHES_DIR.mkdir(parents=True, exist_ok=True)

FILENAME_SAFE = re.compile(r"[^a-zA-Z0-9._\-]+")


def _sanitize_filename(s: str) -> str:
    s2 = FILENAME_SAFE.sub("_", s.strip())
    return s2[:120] if len(s2) > 120 else s2


@dataclass
class GeneratedPatch:
    suggestion: PatchSuggestion
    path: Path
    bytes: int


def _make_patch_filename(idx: int, ps: PatchSuggestion) -> str:
    base = _sanitize_filename(Path(ps.file).name or "patch")
    fn = f"{idx:02d}_{base}.patch"
    return fn


def _normalize_pseudo_diff(diff_text: str) -> str:
    """
    擬似diffが unified diff 風であれば、そのまま保存。
    先頭に '--- a/..' / '+++ b/..' が無い場合は、テキストブロックとして保存しつつ
    注意書きを付与してレビュワーが目視可能にする。
    """
    t = (diff_text or "").rstrip()
    if not t:
        return ""
    lines = t.splitlines()
    has_headers = any(l.startswith("--- ") for l in lines) and any(l.startswith("+++ ") for l in lines)
    if has_headers:
        return t + "\n"
    # ヘッダ無し → そのままブロックとして保存（後段の適用器は対象外）
    wrapped = []
    wrapped.append("# NOTE: This patch was generated from a pseudo diff without unified-diff headers.")
    wrapped.append("#       Please review and convert to a proper unified diff before applying.")
    wrapped.append("")
    wrapped.extend(lines)
    return "\n".join(wrapped) + "\n"


def generate_patches(inv: InventorOutput) -> List[GeneratedPatch]:
    """
    InventorOutput.patch_suggestions から .patch ファイル群を生成して保存。
    - (検出できず) 等はスキップ
    - 擬似diffはそのまま保存（unified diff でない場合は注意書き付き）
    戻り値: GeneratedPatch のリスト
    """
    results: List[GeneratedPatch] = []
    idx = 1
    for ps in inv.patch_suggestions or []:
        if not ps.file or ps.file.startswith("("):
            # 「要ログ確認」等の曖昧提案は物理パッチを作らない
            continue
        content = _normalize_pseudo_diff(ps.pseudo_diff or "")
        if not content.strip():
            continue
        fn = _make_patch_filename(idx, ps)
        out_path = PATCHES_DIR / fn
        out_path.write_text(content, encoding="utf-8")
        results.append(GeneratedPatch(suggestion=ps, path=out_path, bytes=out_path.stat().st_size))
        idx += 1
    return results


def write_index_md(inv: InventorOutput, generated: List[GeneratedPatch]) -> Path:
    """
    生成したパッチの目次 Markdown を作成。
    """
    md = []
    md.append("# Inventor Generated Patches\n")
    if not generated:
        md.append("_No patch files were generated (no concrete suggestions)._")
    else:
        md.append("Below are patch files generated from Inventor suggestions.\n")
        for i, gp in enumerate(generated, 1):
            ps = gp.suggestion
            rel = gp.path.relative_to(REPORTS_DIR).as_posix()
            md.append(f"## {i}. `{ps.file}` :: `{ps.function}`")
            md.append(f"- **Patch**: `/{rel}`  ({gp.bytes} bytes)")
            md.append(f"- **Rationale**: {ps.rationale}")
            md.append("")
    index_path = REPORTS_DIR / "patches_index.md"
    index_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return index_path
