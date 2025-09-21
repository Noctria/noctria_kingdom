# src/codex/tools/ruff_runner.py
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# =============================================================================
# 設定
# =============================================================================
LOGGER = logging.getLogger("ruff_runner")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT / "src" / "codex_reports"
PATCH_DIR = REPORTS_DIR / "patches"
RUFF_JSON_DIR = REPORTS_DIR / "ruff"

for d in [REPORTS_DIR, PATCH_DIR, RUFF_JSON_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# =============================================================================
# ユーティリティ
# =============================================================================
def run_cmd(args: List[str]) -> subprocess.CompletedProcess:
    LOGGER.info("Running: %s", " ".join(args))
    return subprocess.run(args, capture_output=True, text=True)


def save_patch(diff_text: str, prefix: str = "ruff_autofix") -> Path:
    """生成されたパッチを保存して返す"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = PATCH_DIR / f"{prefix}_{ts}.patch"
    path.write_text(diff_text, encoding="utf-8")
    LOGGER.info("Saved patch: %s", path)
    return path


def save_json(data: Dict[str, Any], filename: str) -> Path:
    path = RUFF_JSON_DIR / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Saved JSON: %s", path)
    return path


# =============================================================================
# 実行ロジック
# =============================================================================
def run_ruff(
    targets: List[str],
    fix: bool = False,
    extra_args: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ruff を実行して結果を dict で返す
    """
    cmd = ["ruff", "check"]
    if fix:
        cmd.append("--fix")
    if extra_args:
        cmd.extend(extra_args.split())

    cmd.extend(targets)

    proc = run_cmd(cmd)

    result: Dict[str, Any] = {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run ruff with unified output")
    parser.add_argument("targets", nargs="*", help="Target files or directories")
    parser.add_argument("--fix", action="store_true", help="Apply fixes")
    parser.add_argument("--output-json", type=str, default="last_run.json", help="JSON出力先")
    parser.add_argument("--extra-args", type=str, help="Extra args to pass to ruff (string)")
    args = parser.parse_args(argv)

    if not args.targets:
        LOGGER.error("No targets specified")
        return 1

    result = run_ruff(args.targets, fix=args.fix, extra_args=args.extra_args)

    # JSON 保存
    save_json(result, args.output_json)

    # stdout/stderr を画面にも出力
    print("==== Ruff Runner ====")
    print(f"$ {' '.join(result['command'])}")
    print(f"--- returncode: {result['returncode']}")
    if result["stdout"]:
        print("--- stdout ---")
        print(result["stdout"])
    if result["stderr"]:
        print("--- stderr ---")
        print(result["stderr"])
    print(f"JSON: {RUFF_JSON_DIR / args.output_json}")

    # diff があればパッチ保存
    if args.fix and result["stdout"]:
        patch = save_patch(result["stdout"])
        print(f"patch: {patch}")

    return result["returncode"]


if __name__ == "__main__":
    sys.exit(main())
