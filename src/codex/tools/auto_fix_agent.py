# src/codex/tools/auto_fix_agent.py
from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOG = logging.getLogger("auto_fix_agent")
if not LOG.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# ---------------------------
# Ruff diagnostic data model
# ---------------------------
@dataclass
class Location:
    row: int
    column: int


@dataclass
class Diag:
    code: str
    filename: str
    message: str
    location: Location

    @staticmethod
    def from_obj(obj: Dict) -> "Diag":
        loc = obj.get("location", {}) or {}
        return Diag(
            code=obj.get("code", ""),
            filename=obj.get("filename", ""),
            message=obj.get("message", ""),
            location=Location(row=int(loc.get("row", 0) or 0), column=int(loc.get("column", 0) or 0)),
        )


# ---------------------------
# Ruff runner (JSON)
# ---------------------------
def run_ruff_json(paths: List[str]) -> List[Diag]:
    """Run `ruff check --format json` and parse diagnostics."""
    cmd = ["ruff", "check", "--format", "json", *paths]
    LOG.info("Running: %s", " ".join(cmd))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        LOG.error("ruff が見つかりません。`pip install ruff` を実行してください。")
        sys.exit(2)

    if res.returncode not in (0, 1):  # 0: no issues, 1: issues found
        LOG.error("ruff 実行に失敗しました (code=%s): %s", res.returncode, res.stderr.strip())
        sys.exit(res.returncode)

    try:
        arr = json.loads(res.stdout or "[]")
    except Exception as e:
        LOG.error("ruff JSON の解析に失敗: %s", e)
        LOG.debug("stdout(raw)=%r", res.stdout[:1000])
        return []

    return [Diag.from_obj(x) for x in arr]


# ---------------------------
# Text utilities
# ---------------------------
def _read_lines(p: Path) -> List[str]:
    return p.read_text(encoding="utf-8").splitlines(keepends=True)


def _write_lines(p: Path, lines: List[str]) -> None:
    p.write_text("".join(lines), encoding="utf-8")


def _append_noqa(line: str, code: str) -> str:
    if f"# noqa: {code}" in line:
        return line
    if "# noqa" in line:
        # 既存の noqa にコードを追記
        return re.sub(r"# noqa(?::\s*([A-Z0-9, ]+))?",
                      lambda m: "# noqa: " + ((m.group(1) + ", " if m.group(1) else "") + code),
                      line, count=1)
    # 末尾に付与（コメントや改行を壊さない）
    m = re.search(r"(\r?\n)$", line)
    if m:
        return line[:m.start()] + f"  # noqa: {code}" + m.group(1)
    return line.rstrip("\n") + f"  # noqa: {code}\n"


# ---------------------------
# Fixers
# ---------------------------
def fix_F401(line: str, message: str) -> Tuple[str, bool]:
    """
    Remove unused import safely.
    - from X import a, b  -> remove target name; delete line if empty
    - import x, y         -> remove target name; delete line if empty
    Fallback: add '# noqa: F401'
    """
    # 例: "'pathlib.Path' imported but unused" / "Remove unused import: `pathlib.Path`"
    sym = None
    m1 = re.search(r"'([^']+)' imported but unused", message)
    m2 = re.search(r"`([^`]+)`", message)
    if m1:
        sym = m1.group(1)
    elif m2:
        sym = m2.group(1)

    if sym is None:
        return _append_noqa(line, "F401"), True

    short = sym.split(".")[-1].strip()

    # from ... import ...
    m = re.match(r"(\s*)from\s+([\w\.]+)\s+import\s+(.+)", line)
    if m:
        indent, mod, names = m.groups()
        # 括弧有無を許容しつつ分割
        inner = names.strip().strip("()")
        parts = [p.strip() for p in inner.split(",")]
        new_parts = [p for p in parts if re.split(r"\s+as\s+", p)[0] != short]
        if len(new_parts) == len(parts):
            # 一致せず → 安全に noqa
            return _append_noqa(line, "F401"), True
        if not new_parts:
            # 何も残らないなら行ごと削除
            return "", True
        joined = ", ".join(new_parts)
        out = f"{indent}from {mod} import {joined}\n"
        return out, True

    # import ...
    m = re.match(r"(\s*)import\s+(.+)", line)
    if m:
        indent, names = m.groups()
        parts = [p.strip() for p in names.split(",")]
        new_parts = []
        changed = False
        for p in parts:
            base = re.split(r"\s+as\s+", p)[0]
            base_short = base.split(".")[-1]
            if base == sym or base_short == short:
                changed = True
                continue
            new_parts.append(p)
        if not changed:
            return _append_noqa(line, "F401"), True
        if not new_parts:
            return "", True
        return f"{indent}import {', '.join(new_parts)}\n", True

    # import 文ではない（マルチライン等）→ とりあえず抑制
    return _append_noqa(line, "F401"), True


def fix_F841(line: str, message: str) -> Tuple[str, bool]:
    """
    Unused local variable -> 変数名を '_' または '_<name>' へ。
    型注釈・複合代入にもそこそこ耐える簡易置換。
    """
    # 例: "Local variable `policy` is assigned to but never used"
    m = re.search(r"Local variable [`']?([A-Za-z_]\w*)[`']? is assigned to but never used", message)
    if not m:
        return _append_noqa(line, "F841"), True

    name = m.group(1)

    # パターン:  name[:type]? = ...
    # 置換:      _ = ...  または _name = ...
    # 既に _ プレフィクスならそのまま
    if name.startswith("_"):
        return line, False

    # アノテーション保持
    def _repl(m2: re.Match) -> str:
        head = m2.group(1) or ""
        annot = m2.group(2) or ""
        eq = m2.group(3) or "="
        return f"{head}_{name}{annot} {eq}"

    pat = rf"(^|\s|,){name}(\s*:\s*[^=]+)?\s*(=)"
    new_line, n = re.subn(pat, _repl, line, count=1)
    if n == 0:
        # 複雑なら抑制に退避
        return _append_noqa(line, "F841"), True
    return new_line, True


def fix_E402(line: str, _message: str) -> Tuple[str, bool]:
    """Module level import not at top -> 行末に `# noqa: E402` を付与。"""
    if re.match(r"\s*(from\s+\S+\s+import\s+|import\s+)", line):
        return _append_noqa(line, "E402"), True
    return line, False


FIXERS = {
    "F401": fix_F401,
    "F841": fix_F841,
    "E402": fix_E402,
}


# ---------------------------
# Apply fixes per file
# ---------------------------
def apply_fixes(file_path: Path, diags: List[Diag]) -> Tuple[int, int]:
    """
    指定ファイルへフィックス適用。
    戻り値: (applied_count, kept_count)
    """
    if not file_path.exists():
        return (0, 0)

    lines = _read_lines(file_path)
    # 行番号ベースで後ろから適用（行ずれ防止）
    targets = sorted([d for d in diags if Path(d.filename) == file_path],
                     key=lambda d: d.location.row, reverse=True)

    applied = 0
    kept = 0
    for d in targets:
        if d.code not in FIXERS:
            kept += 1
            continue
        line_idx = max(0, d.location.row - 1)
        if line_idx >= len(lines):
            kept += 1
            continue
        orig = lines[line_idx]
        new, changed = FIXERS[d.code](orig, d.message)
        if changed and new != orig:
            lines[line_idx] = new
            applied += 1
        elif changed and new == "":
            # 行ごと削除
            del lines[line_idx]
            applied += 1
        else:
            kept += 1

    if applied:
        _write_lines(file_path, lines)
    return (applied, kept)


# ---------------------------
# (Optional) GPT escalation
# ---------------------------
def gpt_escalate(_unfixed: List[Diag], _paths: List[str]) -> None:
    """
    ここは土台だけ。必要になったら実装を拡張：
      - 失敗箇所の抜粋 + ルール説明をプロンプトにしてパッチ案を生成
      - .patch を出力して human-in-the-loop で適用
    """
    LOG.info("[GPT] escalation stub: %d items (not implemented yet)", len(_unfixed))
    LOG.info("必要になったら openai ライブラリ呼び出しを実装してください。")


# ---------------------------
# CLI
# ---------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Auto-fix common Ruff issues (F401/F841/E402) with minimal changes.")
    ap.add_argument("--use-gpt", action="store_true", help="未対応ルールをGPTに委譲（実装はスタブ）")
    ap.add_argument("--run-ruff", action="store_true", help="開始前に ruff JSON を最新化してから処理")
    ap.add_argument("paths", nargs="+", help="対象ファイル（またはディレクトリ）")
    args = ap.parse_args(argv)

    # ruff JSON を取得
    diags = run_ruff_json(args.paths) if args.run_ruff else run_ruff_json(args.paths)
    if not diags:
        LOG.info("Ruff の指摘はありません。終了します。")
        return 0

    # ファイル別にまとめて適用
    by_file: Dict[Path, List[Diag]] = {}
    for d in diags:
        by_file.setdefault(Path(d.filename), []).append(d)

    total_applied = 0
    total_kept = 0
    total_files = 0

    for p, dd in by_file.items():
        total_files += 1
        applied, kept = apply_fixes(p, dd)
        total_applied += applied
        total_kept += kept
        LOG.info("Fixed %d, kept %d @ %s", applied, kept, p)

    LOG.info("SUMMARY: files=%d, applied=%d, remaining=%d", total_files, total_applied, total_kept)

    # 追加で ruff を再実行して状況を出すと気持ちいい
    try:
        res = subprocess.run(["ruff", "check", *args.paths], text=True)
        return res.returncode
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
