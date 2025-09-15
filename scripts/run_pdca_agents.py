#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_pdca_agents.py
------------------
PDCA 自動実行のオーケストレーター（ローカル用）。

流れ:
  1) pytest を JUnit XML 付きで実行
  2) ruff を JSON 出力で実行
  3) Inventor (提案) → Harmonia (レビュー) を生成
  4) git: ブランチ作成/切替 → allowed_files.txt にマッチする変更だけ add/commit
  5) 必要なら push (NOCTRIA_PDCA_GIT_PUSH=1)

環境:
  - .env は外側で読み込んでおく想定（例: `set -a && source .env && set +a`）
  - PYTHONPATH はリポジトリ直下を指すこと（例: `export PYTHONPATH="$PWD"`）
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import datetime as dt
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------
# 定数 / パス
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "src" / "codex_reports"
RUFF_DIR = REPORT_DIR / "ruff"
JUNIT_XML = REPORT_DIR / "pytest_last.xml"
INVENTOR_MD = REPORT_DIR / "inventor_suggestions.md"
HARMONIA_MD = REPORT_DIR / "harmonia_review.md"
RUFF_JSON = RUFF_DIR / "ruff.json"

DEFAULT_BRANCH = os.getenv("NOCTRIA_PDCA_BRANCH", "dev/pdca-tested")
WANT_PUSH = (os.getenv("NOCTRIA_PDCA_GIT_PUSH", "0").strip().lower() in {"1", "true", "yes", "on"})
PYTEST_ARGS_ENV = os.getenv("NOCTRIA_PYTEST_ARGS", "")  # 追加引数を渡したいときに使用

# Harmonia を API 呼び出し無しのオフライン判定へ（安全のため既定で offline）
os.environ.setdefault("NOCTRIA_HARMONIA_MODE", "offline")


# ---------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: List[str] | str, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """サブプロセス実行。stdout/stderr を返す。"""
    shell = isinstance(cmd, str)
    display = cmd if shell else " ".join(shlex.quote(c) for c in cmd)  # type: ignore
    log(f"[run] {display}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        shell=shell,
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_dirs() -> None:
    RUFF_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def ts_jst() -> str:
    jst = dt.timezone(dt.timedelta(hours=9))
    return dt.datetime.now(tz=jst).isoformat(timespec="seconds")


# ---------------------------------------------------------------------
# Pytest 実行 & 失敗抽出
# ---------------------------------------------------------------------
@dataclass
class FailureCase:
    nodeid: str
    message: str
    traceback: str
    duration: Optional[float] = None


def run_pytest(junit_xml: Path = JUNIT_XML) -> Dict[str, Any]:
    """pytest を実行し、JUnit XML を保存してサマリを返す。"""
    args = ["-q", "--maxfail=1", "--disable-warnings", "-rA", f"--junitxml={junit_xml}"]
    if PYTEST_ARGS_ENV.strip():
        # 例: "tests -k not slow --durations=10"
        extra = shlex.split(PYTEST_ARGS_ENV)
        args = extra + [*args]

    rc, _, _ = run(["pytest", *args])
    # rc をそのまま返すと PDCA が止まるので、以降の解析に任せる
    summary = parse_junit(junit_xml)
    summary["returncode"] = rc
    return summary


def parse_junit(path: Path) -> Dict[str, Any]:
    """JUnit XML から失敗ケースを抽出。無ければ all green として扱う。"""
    out: Dict[str, Any] = {
        "total": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "cases": [],  # FailureCase の dict
    }
    if not path.exists():
        return out

    try:
        root = ET.parse(path).getroot()
    except Exception:
        return out

    tests = 0
    failures = 0
    errors = 0
    skipped = 0
    cases: List[Dict[str, Any]] = []

    # <testsuite> or <testsuites>
    suites = []
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = root.findall("testsuite")

    for suite in suites:
        try:
            tests += int(suite.attrib.get("tests", "0"))
            failures += int(suite.attrib.get("failures", "0"))
            errors += int(suite.attrib.get("errors", "0"))
            skipped += int(suite.attrib.get("skipped", "0"))
        except Exception:
            pass

        for tc in suite.findall("testcase"):
            name = tc.attrib.get("name", "")
            classname = tc.attrib.get("classname", "")
            nodeid = f"{classname}::{name}" if classname else name
            duration = None
            try:
                duration = float(tc.attrib.get("time", "0") or 0.0)
            except Exception:
                duration = None

            # failure / error ノードを抽出
            tb_text = ""
            msg = ""
            f_node = tc.find("failure")
            e_node = tc.find("error")
            if f_node is not None:
                tb_text = (f_node.text or "").strip()
                msg = f_node.attrib.get("message", "") or "failure"
            elif e_node is not None:
                tb_text = (e_node.text or "").strip()
                msg = e_node.attrib.get("message", "") or "error"
            else:
                continue  # pass/skip はここではスキップ

            cases.append(
                {
                    "nodeid": nodeid,
                    "message": msg,
                    "traceback": tb_text,
                    "duration": duration,
                }
            )

    out.update(
        {
            "total": tests,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
            "cases": cases,
        }
    )
    return out


# ---------------------------------------------------------------------
# Ruff 実行
# ---------------------------------------------------------------------
def run_ruff(out_path: Path = RUFF_JSON) -> Dict[str, Any]:
    """ruff を JSON で出力。返り値は軽いメタ情報。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rc, stdout, _ = run(["ruff", "check", ".", "--output-format=json"])
    # そのまま保存（stdout が JSON）
    try:
        out_path.write_text(stdout, encoding="utf-8")
    except Exception as e:
        log(f"[warn] failed to write ruff json: {e}")

    highlights: List[str] = []
    try:
        rows = json.loads(stdout or "[]")
        # ざっくり上位ルールを 5 件抽出
        counts: Dict[str, int] = {}
        for r in rows:
            code = r.get("code")
            if code:
                counts[code] = counts.get(code, 0) + 1
        for code, cnt in sorted(counts.items(), key=lambda t: t[1], reverse=True)[:5]:
            highlights.append(f"{cnt:4d}  {code}")
    except Exception:
        pass

    return {
        "returncode": rc,
        "highlights": highlights,
        "json_path": str(out_path),
    }


# ---------------------------------------------------------------------
# Inventor / Harmonia 生成
# ---------------------------------------------------------------------
def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def generate_inventor_and_harmonia(pytest_summary: Dict[str, Any], ruff_meta: Dict[str, Any]) -> None:
    """
    pytest の結果から Inventor 提案を作り、Harmonia がレビュー。
    それぞれ Markdown を codex_reports に保存。
    """
    from src.codex.agents.inventor import InventorScriptus
    from src.codex.agents.harmonia import HarmoniaOrdinis

    trace_id = f"pdca_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ctx = {
        "trace_id": trace_id,
        "generated_at": ts_jst(),
        "pytest_summary": {
            "total": pytest_summary.get("total", 0),
            "failed": pytest_summary.get("failures", 0),
            "errors": pytest_summary.get("errors", 0),
            "skipped": pytest_summary.get("skipped", 0),
        },
    }

    inv = InventorScriptus()
    # Ruff 結果（任意表示）
    if ruff_meta and ruff_meta.get("json_path"):
        try:
            # ここでは JSON を直接は読まないが、要約を表示
            hi = "\n".join(ruff_meta.get("highlights", []) or [])
            ruff_summary = textwrap.dedent(
                f"""
                ### Ruff summary
                - Return code: {ruff_meta.get('returncode')}
                - JSON: `{ruff_meta.get('json_path')}`
                ```
                {hi}
                ```
                """
            ).strip()
        except Exception:
            ruff_summary = "Ruff summary unavailable."
    else:
        ruff_summary = "Ruff not executed."

    # 失敗の有無で分岐（構造化 / markdown どちらでも良い）
    failures = pytest_summary.get("cases", []) or []
    inventor_md: str
    if not failures:
        inventor_md = (
            "# 🛠️ Inventor Scriptus — 修正案（Lv1）\n\n"
            f"- Generated: `{ctx['generated_at']}`\n"
            f"- Trace ID: `{trace_id}`\n"
            f"- Pytest: total={ctx['pytest_summary']['total']}, failed=0, errors=0\n\n"
            "✅ 失敗はありません。提案は不要です。\n\n"
            + ruff_summary
        )
    else:
        inventor_md = inv.propose_fixes(failures=failures, context=ctx)
        inventor_md += "\n\n" + ruff_summary

    write_text(INVENTOR_MD, inventor_md)

    # Harmonia レビュー
    harmonia = HarmoniaOrdinis()
    harmonia_md = harmonia.review_markdown(
        failures=failures,
        inventor_suggestions=inventor_md,
        principles=[
            "最小差分・後方互換を優先",
            "observability（重要経路にログ/メトリクス）",
            "再現手順を必ず明記",
        ],
    )
    write_text(HARMONIA_MD, harmonia_md)


# ---------------------------------------------------------------------
# Git 操作（allowed_files.txt フィルタ付き）
# ---------------------------------------------------------------------
def git_current_branch() -> str:
    rc, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if rc == 0 else ""


def git_switch_create(branch: str) -> None:
    cur = git_current_branch()
    if cur == branch:
        log(f"[git] already on '{branch}'")
        return
    rc, _, _ = run(["git", "switch", branch])
    if rc != 0:
        run(["git", "switch", "-c", branch])


def git_status_changed() -> List[str]:
    rc, out, _ = run(["git", "status", "--porcelain"])
    if rc != 0:
        return []
    changed: List[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # format: XY <path>
        changed.append(line[3:].strip())
    return changed


def read_allowed_prefixes(path: Path = ROOT / "allowed_files.txt") -> List[str]:
    pref: List[str] = []
    if not path.exists():
        return pref
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("./"):
            s = s[2:]
        pref.append(s)
    return pref


def filter_allowed(paths: Iterable[str], prefixes: List[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        r = p.lstrip("./")
        if any(r.startswith(px) for px in prefixes):
            out.append(p)
    return out


def git_commit_allowed(branch: str, msg: str) -> bool:
    git_switch_create(branch)

    changed = git_status_changed()
    if not changed:
        log("[git] no changes detected.")
        return False

    allowed_prefixes = read_allowed_prefixes()
    if not allowed_prefixes:
        log("✋ BLOCK: allowed_files.txt が空または未設置のため、自動コミットをスキップします。")
        return False

    allowed_only = filter_allowed(changed, allowed_prefixes)
    if not allowed_only:
        log("ℹ️ allowed_files に一致する変更がありません。コミットしません。")
        return False

    run(["git", "add", *allowed_only])
    rc, out, err = run(["git", "commit", "-m", msg])
    if rc != 0:
        sys.stderr.write(err)
        log("✋ BLOCK: コミットに失敗しました。")
        return False

    if WANT_PUSH:
        run(["git", "push", "-u", "origin", branch])
    return True


# ---------------------------------------------------------------------
# main
# ---------------------------------------------------------------------
def main() -> int:
    os.chdir(ROOT)
    ensure_dirs()

    parser = argparse.ArgumentParser(description="Run PDCA agents locally.")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="commit/push に使うブランチ名")
    args = parser.parse_args()

    # 1) pytest
    pyres = run_pytest(JUNIT_XML)

    # 2) ruff
    ruff_meta = run_ruff(RUFF_JSON)

    # 3) Inventor & Harmonia
    try:
        generate_inventor_and_harmonia(pyres, ruff_meta)
    except Exception as e:
        log(f"[warn] failed to render Inventor/Harmonia: {e}")

    # 4) commit (allowed のみ)
    commit_msg = f"pdca: tested {dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    committed = git_commit_allowed(args.branch, commit_msg)
    if committed:
        log("[done] PDCA agents committed changes.")
    else:
        log("[done] PDCA agents finished (no commit).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
