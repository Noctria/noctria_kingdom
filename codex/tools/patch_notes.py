# codex/tools/patch_notes.py
from __future__ import annotations

import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_JSON = "codex_reports/tmp.json"
DEFAULT_OUT = "codex_reports/patch_notes.md"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_summary(d: Dict[str, Any]) -> Dict[str, Any]:
    # pytest-json-report の一般的な構造に防御的に対応
    summary = d.get("summary") or {}
    totals = {
        "total": summary.get("total") or len(d.get("tests", [])),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "error": summary.get("errors", 0) or summary.get("error", 0),
        "skipped": summary.get("skipped", 0),
        "xfailed": summary.get("xfailed", 0),
        "xpassed": summary.get("xpassed", 0),
        "duration": summary.get("duration", None),
        "collected": summary.get("collected", None),
    }
    return totals


def _extract_phase_repr(phase: Dict[str, Any]) -> str:
    if not isinstance(phase, dict):
        return ""
    # 可能なキーを順に探す
    for k in ("crash", "longrepr", "stdout", "stderr", "reprcrash", "reprtraceback"):
        v = phase.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, dict):
            # reprcrash / reprtraceback フォーマット
            msg = v.get("message") or v.get("path") or ""
            if msg:
                return str(msg)
    return ""


def _extract_test_message(t: Dict[str, Any]) -> Tuple[str, str]:
    """
    returns (phase, message)
    phase is one of: setup/call/teardown/collect
    """
    # 優先度: call -> setup -> teardown -> collect
    for phase_name in ("call", "setup", "teardown", "collect"):
        phase = t.get(phase_name)
        msg = _extract_phase_repr(phase or {})
        if msg:
            return phase_name, msg
    # fallback
    return "call", ""


def _shorten(text: str, limit: int = 800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    head = text[: limit // 2].rstrip()
    tail = text[-limit // 2 :].lstrip()
    return f"{head}\n...\n{tail}"


def _mk_failed_entries(tests: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for t in tests:
        nodeid = t.get("nodeid", "<unknown>")
        outcome = t.get("outcome", "failed")
        phase, msg = _extract_test_message(t)
        dur = (t.get(phase, {}) or {}).get("duration", None)

        lines.append(f"- **{nodeid}**  *(outcome: {outcome}, phase: {phase}, duration: {dur}s)*")
        if msg:
            lines.append("")
            lines.append("  <details><summary>Traceback / message</summary>\n\n```text")
            lines.append(_shorten(msg, 1600))
            lines.append("```\n</details>")
        lines.append("")
        lines.append("  **Fix TODO:**")
        lines.append("  - [ ] 原因の仮説：")
        lines.append("  - [ ] 再現手順：")
        lines.append("  - [ ] 対応方針：")
        lines.append("  - [ ] 最小修正パッチ案：")
        lines.append("")
    return lines


def _mk_skipped_entries(tests: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for t in tests:
        nodeid = t.get("nodeid", "<unknown>")
        reason = ""
        # skip 理由は setup/call に入ることが多い
        for phase_name in ("setup", "call"):
            phase = t.get(phase_name) or {}
            r = phase.get("longrepr") or phase.get("crash") or ""
            if isinstance(r, str) and r:
                reason = r
                break
        lines.append(f"- **{nodeid}**")
        if reason:
            lines.append("  <details><summary>Skip reason</summary>\n\n```text")
            lines.append(_shorten(reason, 800))
            lines.append("```\n</details>")
        lines.append("")
    return lines


def make_patch_notes(json_path: str = DEFAULT_JSON, out_path: str = DEFAULT_OUT) -> None:
    """
    pytest-json-report の出力 (json_path) から
    codex_reports/patch_notes.md (out_path) を生成する
    """
    json_p = Path(json_path)
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    data = _read_json(json_p)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if not data:
        # JSON がない場合でもプレースホルダを出す
        placeholder = textwrap.dedent(
            f"""\
            ## Patch Notes (placeholder)
            - generated: {now}
            - note: JSON report not found at `{json_path}`. Run pytest with:
              ```
              pytest -q tests --json-report --json-report-file={json_path}
              ```
            """
        )
        out_p.write_text(placeholder, encoding="utf-8")
        return

    env = data.get("environment", {})
    summary = _get_summary(data)
    tests: List[Dict[str, Any]] = data.get("tests", [])

    failed = [t for t in tests if t.get("outcome") == "failed"]
    errors = [t for t in tests if t.get("outcome") == "error"]
    skipped = [t for t in tests if t.get("outcome") == "skipped"]
    xfailed = [t for t in tests if t.get("outcome") == "xfailed"]
    xpassed = [t for t in tests if t.get("outcome") == "xpassed"]

    lines: List[str] = []

    # Header
    lines.append("# Patch Notes (Codex manual fix guide)")
    lines.append("")
    lines.append(f"- generated: **{now}**")
    lines.append(f"- source json: `{json_path}`")
    lines.append(f"- Codex Scope: `{os.environ.get('CODEX_SCOPE', 'light')}`")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| total | passed | failed | error | skipped | xfailed | xpassed | duration |")
    lines.append("|------:|------:|------:|-----:|-------:|-------:|--------:|---------:|")
    lines.append(
        f"| {summary.get('total', 0)} | {summary.get('passed', 0)} | {summary.get('failed', 0)} | "
        f"{summary.get('error', 0)} | {summary.get('skipped', 0)} | {summary.get('xfailed', 0)} | "
        f"{summary.get('xpassed', 0)} | {summary.get('duration', 'N/A')} |"
    )
    lines.append("")

    # Environment (抜粋)
    if env:
        lines.append("### Environment (excerpt)")
        lines.append("")
        for k in sorted(env.keys()):
            v = env.get(k)
            if k.lower() in {"platform", "python", "plugins"}:
                lines.append(f"- **{k}**: {v}")
        lines.append("")

    # Failures & Errors
    if failed or errors:
        lines.append("## ❌ Failed / Error Tests")
        lines.append("")
        lines.extend(_mk_failed_entries(failed + errors))
    else:
        lines.append("## ✅ No failures")
        lines.append("")

    # Skips
    if skipped:
        lines.append("## ⏭ Skipped Tests")
        lines.append("")
        lines.extend(_mk_skipped_entries(skipped))

    # Xfail / Xpass
    if xfailed or xpassed:
        lines.append("## ⚠️ Expected Fail / Unexpected Pass")
        lines.append("")
        if xfailed:
            lines.append(f"- xfailed: {len(xfailed)}")
        if xpassed:
            lines.append(f"- xpassed: {len(xpassed)}")
        lines.append("")

    # Next actions template
    lines.append("## Suggested Next Actions")
    lines.append("")
    lines.append("- [ ] 失敗テストの最小再現を作る（入力データを固定化、乱数seedを固定）")
    lines.append("- [ ] 修正パッチを作成（影響範囲を特定、回帰テストを追加）")
    lines.append("- [ ] `scripts/local_ci.sh` で fast subset を通す")
    lines.append("- [ ] `CODEX_FULL=1 ./scripts/local_ci.sh` で full を通す（必要に応じて）")
    lines.append("- [ ] `codex/patches/` にパッチを保存 or Git ブランチを切って PR 作成")
    lines.append("")

    out_p.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    # CLI 実行: 引数に json_path / out_path を渡せる
    json_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSON
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    make_patch_notes(json_path, out_path)
