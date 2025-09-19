#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os, sys, json, shlex, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
os.chdir(ROOT)

# sys.path に src を追加して import エラーを防ぐ
for p in (ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

JST = timezone(timedelta(hours=9))
TRACE_ID = datetime.now(JST).strftime("pdca_%Y%m%d_%H%M%S")

# --- optional: load .env if present (for local runs)
try:
    from dotenv import load_dotenv  # type: ignore
    env_path = ROOT / ".env"
    load_dotenv(env_path, override=True)
    print(f"[env] Loaded {env_path}")
except Exception as e:
    print(f"[env] dotenv not loaded: {e}")

# === DB utils（存在しなくても動くフェイルソフト） ===
try:
    from scripts._pdca_db import (
        start_run, finish_run, log_message, save_artifact, save_tests, save_lint, log_commit
    )
except Exception:
    def start_run(*a, **k): pass
    def finish_run(*a, **k): pass
    def log_message(*a, **k): pass
    def save_artifact(*a, **k): pass
    def save_tests(*a, **k): pass
    def save_lint(*a, **k): pass
    def log_commit(*a, **k): pass

# === Scribe（史官） ===
try:
    from scripts._scribe import log_chronicle
except Exception:
    def log_chronicle(*a, **k): pass

# === Agents ===
from src.codex.agents.inventor import InventorScriptus, InventorOutput
from src.codex.agents import harmonia as H
from src.strategies.hermes_cognitor import HermesCognitorStrategy

# --- helpers -----------------------------------------------------------------
def run(cmd: str, allow_fail: bool = False, cwd: Path | None = None) -> Tuple[int, str, str]:
    print(f"[run] {cmd}")
    p = subprocess.run(cmd, shell=True, cwd=str(cwd or ROOT), text=True, capture_output=True)
    if p.stdout: print(p.stdout, end="")
    if p.stderr: print(p.stderr, end="", file=sys.stderr)
    if p.returncode != 0 and not allow_fail:
        raise SystemExit(p.returncode)
    return p.returncode, p.stdout, p.stderr


def parse_junit(junit_path: Path) -> dict:
    try:
        import xml.etree.ElementTree as ET
        root = ET.parse(junit_path).getroot()
        total = failed = errors = skipped = 0
        for suite in root.findall("testsuite"):
            total += int(suite.attrib.get("tests", 0))
            failed += int(suite.attrib.get("failures", 0))
            errors += int(suite.attrib.get("errors", 0))
            skipped += int(suite.attrib.get("skipped", 0))
        passed = max(0, total - failed - errors - skipped)
        return {"total": total, "passed": passed, "failed": failed, "errors": errors, "skipped": skipped}
    except Exception:
        return {"total": None, "passed": None, "failed": None, "errors": None, "skipped": None}


def git_commit_push(stage_files: List[str], branch: str, message: str) -> Tuple[bool, str | None]:
    def _r(args: List[str]) -> Tuple[int, str, str]:
        return run(" ".join(shlex.quote(a) for a in args), allow_fail=True)

    _r(["git", "switch", branch])
    _r(["git", "switch", "-c", branch])  # 既存なら失敗してもOK

    if stage_files:
        _r(["git", "add", *stage_files])
    else:
        return (False, None)

    # ワークツリーの他変更は退避し、ステージ済みのみ commit
    _r(["git", "stash", "-u", "--keep-index"])

    try:
        rc, out, _ = _r(["git", "commit", "-m", message])
        if rc != 0:
            return (False, None)

        rc2, out2, _ = _r(["git", "rev-parse", "HEAD"])
        sha = (out2 or "").strip() if rc2 == 0 else None

        _r(["git", "push", "-u", "origin", branch])
        return (True, sha)
    finally:
        _r(["git", "stash", "pop"])


# --- main --------------------------------------------------------------------
def main() -> int:
    # === Start ===
    start_run(TRACE_ID, notes="nightly PDCA run")
    log_message(TRACE_ID, "orchestrator", "system", "PDCA run started", {"trace_id": TRACE_ID})
    log_chronicle(
        title="PDCA 開始",
        category="note",
        content_md=f"Trace `{TRACE_ID}` で夜間PDCAを開始（Veritas→Inventor→Harmonia→Hermes）。",
        trace_id=TRACE_ID, topic="PDCA nightly", tags=["pdca","nightly"]
    )

    reports_dir = ROOT / "src" / "codex_reports"
    (reports_dir / "ruff").mkdir(parents=True, exist_ok=True)

    # === 1) Lint & Test ===
    junit = reports_dir / "pytest_last.xml"
    ruff_json = reports_dir / "ruff" / "ruff.json"

    run(f"pytest -q --maxfail=1 --disable-warnings -rA --junitxml={junit}", allow_fail=True)
    run(f"ruff check . --output-format=json > {ruff_json}", allow_fail=True)

    test_sum = parse_junit(junit) if junit.exists() else {"failed": None, "errors": None}
    save_tests(TRACE_ID, test_sum, str(junit) if junit.exists() else None)

    try:
        lint_raw = json.loads(ruff_json.read_text(encoding="utf-8")) if ruff_json.exists() else []
        lint_errs = len(lint_raw) if isinstance(lint_raw, list) else 0
    except Exception:
        lint_raw, lint_errs = [], None
    save_lint(TRACE_ID, {"errors": lint_errs, "warnings": 0}, str(ruff_json) if ruff_json.exists() else None)

    log_chronicle(
        title="テスト/リンタ結果",
        category="kpi",
        content_md=(
            f"- pytest: total={test_sum.get('total')}, passed={test_sum.get('passed')}, "
            f"failed={test_sum.get('failed')}, errors={test_sum.get('errors')}\n"
            f"- ruff errors={lint_errs}"
        ),
        trace_id=TRACE_ID, topic="PDCA nightly"
    )

    # === 2) Inventor 提案 → Harmonia レビュー（API/オフライン自動切替） ===
    inv_agent = InventorScriptus()
    pytest_result = {"failures": [], "trace_id": TRACE_ID}
    inventor_out: InventorOutput = inv_agent.propose_fixes_structured(pytest_result)

    inv_md = inventor_out.to_markdown()
    (reports_dir / "inventor_suggestions.md").write_text(inv_md, encoding="utf-8")
    save_artifact(TRACE_ID, "report", str(reports_dir / "inventor_suggestions.md"), inventor_out.to_dict())
    log_message(TRACE_ID, "inventor", "assistant", "inventor_suggestions",
                {"patches": len(inventor_out.patch_suggestions)})

    # 🔑 Harmonia（統合API）：環境で offline/api を自動選択
    review_res = H.review(inventor_out)  # ← ここが統合ポイント
    harm_md = H.HarmoniaOrdinis().to_markdown(review_res)
    (reports_dir / "harmonia_review.md").write_text(harm_md, encoding="utf-8")
    save_artifact(TRACE_ID, "report", str(reports_dir / "harmonia_review.md"),
                  {"verdict": review_res.verdict, "comments": review_res.comments})
    log_message(TRACE_ID, "harmonia", "assistant", "review",
                {"verdict": review_res.verdict, "n_comments": len(review_res.comments)})

    log_chronicle(
        title="修正提案とレビュー",
        category="decision",
        content_md=f"- Inventor: {inventor_out.summary}\n- Harmonia: verdict **{review_res.verdict}**（{len(review_res.comments)} comments）",
        trace_id=TRACE_ID, topic="PDCA nightly",
        refs={"inventor_report": "src/codex_reports/inventor_suggestions.md",
              "harmonia_report": "src/codex_reports/harmonia_review.md"}
    )

    # === 2.5) Hermes 説明生成（API/ローカル自動切替） =======================
    try:
        hermes = HermesCognitorStrategy()
        # Harmoniaの結果を軽く特徴量化して渡す（必要に応じて拡張OK）
        features: Dict[str, Any] = {
            "harmonia_verdict": review_res.verdict,
            "harmonia_comments": len(review_res.comments),
        }
        # 代表ラベル（例）：verdict とコメント数の粗い離散化
        labels: List[str] = [
            f"verdict_{review_res.verdict.lower()}",
            "comments_many" if len(review_res.comments) >= 5 else "comments_few",
        ]
        reason = "Harmonia の審査結果に基づく要約レポートを作成してください。"

        hermes_out = hermes.propose(
            {"features": features, "labels": labels, "reason": reason},
            decision_id=TRACE_ID,
            caller="pdca_orchestrator",
        )
        hermes_md = HermesCognitorStrategy.to_markdown(
            hermes_out["explanation"],
            meta={"llm_model": hermes_out.get("llm_model"),
                  "decision_id": TRACE_ID, "caller": "pdca_orchestrator"},
        )
        (reports_dir / "hermes_explanation.md").write_text(hermes_md, encoding="utf-8")
        save_artifact(TRACE_ID, "report", str(reports_dir / "hermes_explanation.md"), hermes_out)
        log_message(TRACE_ID, "hermes", "assistant", "explanation", {"used_api": os.getenv("HERMES_USE_OPENAI") == "1"})
        log_chronicle(
            title="Hermes 説明生成",
            category="analysis",
            content_md="Hermes explanation generated: レポートを保存しました。",
            trace_id=TRACE_ID, topic="PDCA nightly",
            refs={"hermes_report": "src/codex_reports/hermes_explanation.md"}
        )
    except Exception as e:
        log_message(TRACE_ID, "hermes", "assistant", "skip", {"error": repr(e)})

    # === 3) 緑なら dev ブランチへ push（レポートのみ） =======================
    DEV_BRANCH = os.getenv("NOCTRIA_DEV_BRANCH", "dev/pdca-tested")
    ALLOW_GLOBS = [g.strip() for g in os.getenv(
        "NOCTRIA_DEV_ALLOW_GLOBS",
        "src/codex_reports/**,pdca_reports/**"
    ).split(",") if g.strip()]

    rc, out, _ = run("git status --porcelain", allow_fail=True)
    changed: List[str] = []
    if out:
        for line in out.splitlines():
            if not line.strip():
                continue
            path = line[3:].strip()
            p = Path(path)
            if any(p.match(g) for g in ALLOW_GLOBS):
                changed.append(path)

    ok_tests = (test_sum.get("failed") in (0, None)) and (test_sum.get("errors") in (0, None))
    ok_lint = (lint_errs == 0) or (lint_errs is None)

    if changed and ok_tests:
        success, sha = git_commit_push(changed, DEV_BRANCH, f"pdca: report artifacts ({TRACE_ID})")
        log_commit(TRACE_ID, DEV_BRANCH, sha, changed, "pdca: reports")
        msg = f"devブランチ `{DEV_BRANCH}` へ report push。commit={sha}, files={len(changed)}"
        log_message(TRACE_ID, "orchestrator", "assistant", "git_push",
                    {"branch": DEV_BRANCH, "commit": sha, "files": changed})
        log_chronicle(title="レポートをコミット/プッシュ", category="pr", content_md=msg,
                       trace_id=TRACE_ID, topic="PDCA nightly",
                       refs={"branch": DEV_BRANCH, "commit": sha, "files": changed})
    else:
        reason = "no changes" if not changed else "tests not green"
        log_message(TRACE_ID, "orchestrator", "assistant", "git_skip",
                    {"reason": reason, "ok_tests": ok_tests, "lint_errs": lint_errs})
        log_chronicle(title="自動コミットをスキップ", category="note",
                       content_md=f"理由: {reason}. ok_tests={ok_tests}, lint_errs={lint_errs}",
                       trace_id=TRACE_ID, topic="PDCA nightly")

    # === End ===
    finish_run(TRACE_ID, status="SUCCESS")
    log_chronicle(title="PDCA 完了", category="note",
                  content_md="今回の夜間ループを完了。", trace_id=TRACE_ID, topic="PDCA nightly")
    print("[done] PDCA agents finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
