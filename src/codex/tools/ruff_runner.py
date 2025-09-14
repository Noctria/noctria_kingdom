#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruff_runner.py
- Ruff を指定ターゲットに対して実行
- --fix 指定時は自動修正を実施し、差分をパッチとして保存
- 実行結果の要約を JSON に保存（次段の Inventor/Harmonia で参照しやすく）

使い方:
  python ruff_runner.py tests/unit_tests.py tools/*.py
  python ruff_runner.py --fix tools/scan_repo_to_mermaid.py

推奨: venv_codex を有効化したシェルで実行（ruff が PATH にあること）
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]  # プロジェクト直下を想定（/src の1つ上）
REPORT_DIR = REPO_ROOT / "src" / "codex_reports" / "ruff"
PATCH_DIR = REPO_ROOT / "src" / "codex_reports" / "patches"


def run(cmd: List[str], cwd: Path | None = None) -> Tuple[int, str]:
    """サブプロセスを走らせ、returncode と stdout+stderr を返す。"""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def ensure_dirs() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PATCH_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run ruff with optional --fix and export a patch.")
    ap.add_argument(
        "targets",
        nargs="*",
        help="Files or directories to lint. If omitted, ruff will run on the repo root.",
    )
    ap.add_argument(
        "--fix",
        action="store_true",
        help="Run `ruff check --fix` to apply autofixes, then export a patch if changes exist.",
    )
    ap.add_argument(
        "--output-json",
        default=str(REPORT_DIR / "last_run.json"),
        help="Path to write a JSON summary (default: src/codex_reports/ruff/last_run.json).",
    )
    ap.add_argument(
        "--extra-args",
        default="",
        help="Extra args to pass to ruff (e.g. '--unsafe-fixes').",
    )
    return ap.parse_args()


def build_ruff_cmd(fix: bool, targets: List[str], extra_args: str) -> List[str]:
    cmd = ["ruff", "check"]
    if fix:
        cmd.append("--fix")

    if extra_args:
        cmd += shlex.split(extra_args)

    # ターゲットがなければカレント（repo root）に対して実行
    if targets:
        cmd += targets
    else:
        cmd.append(".")

    return cmd


def export_patch_if_changed(targets: List[str]) -> str | None:
    """
    変更があれば git diff --patch を生成。
    - 対象ファイルに絞りたいが、手軽さ優先でリポジトリ全体の差分を取得。
    - 将来: targets が明示された場合はパスで -- を付けて範囲を絞る最適化も可。
    """
    # 何か変更があるか？
    rc, _ = run(["git", "diff", "--quiet"])
    if rc == 0:
        return None  # 差分なし

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    patch_path = PATCH_DIR / f"ruff_autofix_{ts}.patch"

    # パッチ出力
    run(["git", "diff", "--patch", "--no-ext-diff", "-U3", "-a", "-M", "-C", "-B", "-R"])  # warm-up
    rc, patch = run(["git", "diff", "--patch", "--no-ext-diff", "-U3"])
    if rc not in (0, 1):  # git diff は差分があっても 0/1 を返し得る
        return None

    patch_path.write_text(patch, encoding="utf-8")
    return str(patch_path)


def summarize_ruff_output(output: str) -> Dict[str, Any]:
    """
    超簡易サマリ:
    - 全出力テキスト
    - issue 件数っぽい行の抽出（ruff は最後に 'Found X errors (Y fixed)' のようなまとめを出す）
    """
    summary_lines: List[str] = []
    for line in output.splitlines():
        if "error" in line.lower() or "warning" in line.lower():
            summary_lines.append(line.strip())
        if line.strip().startswith("Found "):  # Ruff のまとめ行
            summary_lines.append(line.strip())

    return {
        "raw": output,
        "highlights": summary_lines[-10:],  # 末尾側の重要そうな行を最大10行
    }


def main() -> int:
    args = parse_args()
    ensure_dirs()

    ruff_cmd = build_ruff_cmd(args.fix, args.targets, args.extra_args)
    rc, out = run(ruff_cmd)

    # 要約を準備
    summary = {
        "cmd": ruff_cmd,
        "returncode": rc,
        "fix_mode": args.fix,
        "cwd": str(REPO_ROOT),
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "result": summarize_ruff_output(out),
        "patch_path": None,
    }

    # --fix の場合は差分をパッチ出力
    if args.fix:
        patch_path = export_patch_if_changed(args.targets)
        if patch_path:
            summary["patch_path"] = patch_path

    # JSON 保存
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 画面にも軽く出す
    print("==== Ruff Runner ====")
    print("$", " ".join(shlex.quote(c) for c in ruff_cmd))
    print("--- returncode:", rc)
    if summary["patch_path"]:
        print("patch:", summary["patch_path"])
    print("--- highlights ---")
    for line in summary["result"]["highlights"]:
        print(line)
    print(f"JSON: {out_json}")

    # そのまま Ruff の終了コードを返す（CI 連携しやすい）
    return rc


if __name__ == "__main__":
    sys.exit(main())
