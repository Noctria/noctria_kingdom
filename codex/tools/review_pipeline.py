# codex/tools/review_pipeline.py
# -*- coding: utf-8 -*-
"""
📦 Codex Review Pipeline — v3.0 (Harmonia Ordinis + Inventor Scriptus)
- pytest JSON を解析して Inventor/Harmonia の Markdown を生成
- Inventor の PatchSuggestion（pseudo_diff）を .patch に書き出し、索引を作成
- 🆕 外部提案ファイル `codex_reports/inventor_suggestions.json`（before/after または unified diff `patch`）にも対応
- 🆕 pytest のサマリを `codex_reports/pytest_summary.md` にも保存（GUI表示用）

入出力（標準配置）:
  PROJECT_ROOT/
    codex_reports/
      tmp.json                        ... pytest-json-report 出力
      inventor_suggestions.md         ... Inventor（本文）
      harmonia_review.md              ... Harmonia（本文）
      pytest_summary.md               ... Pytestサマリ（HUD表示用）
      inventor_suggestions.json       ... 🆕 外部提案（任意）
      patches/
        0001_xxx_YYYYmmdd-HHMMSS.patch
        0002_yyy_YYYYmmdd-HHMMSS.patch
      patches_index.md                ... パッチ一覧

`inventor_suggestions.json` の例:
[
  {
    "title": "Fix missing import in pdca_summary.py",
    "file": "noctria_gui/routes/pdca_summary.py",
    "before": "from __future__ import annotations\n\n# ...",
    "after":  "from __future__ import annotations\nimport json\n\n# ..."
  },
  {
    "title": "Refactor template context building",
    "file": "noctria_gui/routes/codex.py",
    "patch": "--- a/noctria_gui/routes/codex.py\n+++ b/noctria_gui/routes/codex.py\n@@ ...\n- old line\n+ new line\n"
  }
]
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from codex.tools.json_parse import load_json, build_pytest_result_for_inventor

# 既存ヒューリスティック Inventor/Harmonia を利用
from codex.agents.inventor import propose_fixes, InventorOutput, PatchSuggestion
from codex.agents.harmonia import review, ReviewResult

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "codex_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TMP_JSON = REPORTS_DIR / "tmp.json"
INV_MD = REPORTS_DIR / "inventor_suggestions.md"
HAR_MD = REPORTS_DIR / "harmonia_review.md"

# 🆕 追加出力
PYTEST_SUMMARY_MD = REPORTS_DIR / "pytest_summary.md"
INV_JSON = REPORTS_DIR / "inventor_suggestions.json"  # 外部提案（任意）

# 🆕 パッチ保存先 & インデックス
PATCHES_DIR = REPORTS_DIR / "patches"
PATCHES_DIR.mkdir(parents=True, exist_ok=True)
PATCHES_INDEX = REPORTS_DIR / "patches_index.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _md_escape(x: str) -> str:
    return (
        x.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _extract_summary_and_failed_tests(data: Dict[str, Any]) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    pytest-json-report の構造から合計/失敗の要約と、失敗テストの明細を抽出。
    - 失敗が無ければ failed_tests は空配列を返す。
    """
    summary = dict(data.get("summary") or {})
    passed = int(summary.get("passed") or 0)
    total = int(summary.get("total") or summary.get("collected") or 0)
    failed = max(0, total - passed)
    summ = {"passed": passed, "failed": failed, "total": total}

    tests = data.get("tests") or []
    failed_tests: List[Dict[str, Any]] = []
    for t in tests:
        if (t.get("outcome") or "").lower() == "failed":
            # 可能なら longrepr / message を拾う
            msg = ""
            for phase in ("setup", "call", "teardown"):
                phase_obj = t.get(phase)
                if isinstance(phase_obj, dict) and (phase_obj.get("outcome") == "failed"):
                    cand = phase_obj.get("longrepr") or phase_obj.get("crash")
                    if cand:
                        msg = str(cand)
                        break
            failed_tests.append(
                {
                    "nodeid": t.get("nodeid", ""),
                    "lineno": t.get("lineno"),
                    "message": msg,
                }
            )
    return summ, failed_tests


def _render_pytest_summary_md(summary: Dict[str, int], failed_tests: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# 🧪 Pytest Summary")
    lines.append("")
    lines.append(f"- Generated: `{_now_iso()}`")
    lines.append(f"- Passed: **{summary.get('passed',0)}**")
    lines.append(f"- Failed: **{summary.get('failed',0)}**")
    lines.append(f"- Total : **{summary.get('total',0)}**")
    lines.append("")
    if failed_tests:
        lines.append("## ❌ Failures")
        for f in failed_tests:
            tc = f.get("nodeid") or "unknown::test"
            msg = (f.get("message") or "").strip()
            lines.append(f"- **{tc}**")
            if msg:
                lines.append(f"  - `{msg[:350] + ('...' if len(msg)>350 else '')}`")
        lines.append("")
    return "\n".join(lines)


def _slugify(text: str, max_len: int = 40) -> str:
    """
    ファイル名に使える安全なスラッグへ。日本語等もある程度通すが、制御文字や空白を整形。
    """
    if not text:
        return "patch"
    txt = re.sub(r"[^\w\-\.\u00A0-\uFFFF]+", "-", text, flags=re.UNICODE)  # おおざっぱ非単語→ハイフン
    txt = re.sub(r"-{2,}", "-", txt).strip("-_.")
    if not txt:
        txt = "patch"
    if len(txt) > max_len:
        txt = txt[:max_len].rstrip("-_.")
    return txt or "patch"


def _next_seq_num() -> int:
    """
    既存の 0001_*.patch を見て、次の連番を返す。
    """
    max_n = 0
    for p in PATCHES_DIR.glob("*.patch"):
        m = re.match(r"^(\d{4})_", p.name)
        if m:
            try:
                n = int(m.group(1))
                max_n = max(max_n, n)
            except Exception:
                pass
    return max_n + 1


def _scan_patch_files() -> List[Dict[str, Any]]:
    """
    patches/ 内のパッチ一覧（mtime 降順）。
    """
    items: List[Dict[str, Any]] = []
    for p in PATCHES_DIR.glob("*.patch"):
        try:
            stat = p.stat()
            items.append(
                {
                    "path": p,
                    "rel": p.relative_to(REPORTS_DIR).as_posix(),  # "patches/xxx.patch"
                    "name": p.name,
                    "size": stat.st_size,
                    "mtime": _dt.datetime.fromtimestamp(stat.st_mtime).astimezone(),
                }
            )
        except Exception:
            pass
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def _make_unified_diff_from_before_after(file_path: str, before: str, after: str) -> str:
    """
    before/after の文字列から unified diff を生成。
    """
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    a_label = f"a/{file_path}"
    b_label = f"b/{file_path}"

    diff = difflib.unified_diff(
        before_lines, after_lines,
        fromfile=a_label, tofile=b_label,
        fromfiledate=_now_iso(), tofiledate=_now_iso(),
        n=3,
    )
    return "".join(diff)


# ---------------------------------------------------------------------------
# Markdown writers (Inventor/Harmonia)
# ---------------------------------------------------------------------------
def write_inventor_markdown(
    out: InventorOutput,
    *,
    header_note: Optional[str] = None,
    pytest_summary: Optional[Dict[str, int]] = None,
    generated_patches: Optional[List[Tuple[Path, PatchSuggestion]]] = None,
    external_generated: Optional[List[Tuple[Path, Dict[str, Any]]]] = None,
) -> None:
    lines: List[str] = []
    lines.append("# Inventor Scriptus — 修正案")
    lines.append("")
    lines.append(f"- Generated at: `{_now_iso()}`")
    if pytest_summary:
        lines.append(
            f"- Pytest Summary: **{pytest_summary.get('passed',0)}/{pytest_summary.get('total',0)} passed**, "
            f"failed={pytest_summary.get('failed',0)}"
        )
    if header_note:
        lines.append(f"- Note: {_md_escape(header_note)}")
    lines.append("")
    lines.append(f"**Summary**: {_md_escape(out.summary)}")
    lines.append("")
    lines.append("## Root Causes")
    if out.root_causes:
        for r in out.root_causes:
            lines.append(f"- {_md_escape(str(r))}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Patch Suggestions")
    if out.patch_suggestions:
        for i, p in enumerate(out.patch_suggestions, 1):
            lines.append(f"### {i}. `{p.file}` :: `{p.function}`")
            lines.append("")
            lines.append("**Rationale**")
            lines.append("")
            lines.append(f"- {_md_escape(p.rationale)}")
            lines.append("")
            lines.append("**Pseudo Diff**")
            lines.append("")
            lines.append("```diff")
            lines.append(p.pseudo_diff.strip() if p.pseudo_diff else "(N/A)")
            lines.append("```")
            lines.append("")
    else:
        lines.append("- (no suggestions)")
        lines.append("")

    lines.append("## Follow-up tests")
    if out.followup_tests:
        for t in out.followup_tests:
            lines.append(f"- `{t}`")
    else:
        lines.append("- `pytest -q`")
    lines.append("")

    # 🆕 生成済みパッチの一覧（内部：InventorOutput）
    if generated_patches:
        lines.append("## Generated Patches (from InventorOutput)")
        lines.append("")
        for path, p in generated_patches:
            rel = path.relative_to(REPORTS_DIR).as_posix()
            lines.append(f"- [{path.name}]({rel}) — `{p.file}` :: `{p.function}`")
        lines.append("")

    # 🆕 外部JSONから生成されたパッチ一覧
    if external_generated:
        lines.append("## Generated Patches (from inventor_suggestions.json)")
        lines.append("")
        for path, item in external_generated:
            rel = path.relative_to(REPORTS_DIR).as_posix()
            title = item.get("title") or path.stem
            tgt = item.get("file") or "N/A"
            lines.append(f"- [{path.name}]({rel}) — **{_md_escape(title)}** → `{tgt}`")
        lines.append("")

    INV_MD.write_text("\n".join(lines), encoding="utf-8")


def write_harmonia_markdown(
    rv: ReviewResult,
    *,
    header_note: Optional[str] = None,
    pytest_summary: Optional[Dict[str, int]] = None
) -> None:
    lines: List[str] = []
    lines.append("# Harmonia Ordinis — レビューレポート")
    lines.append("")
    lines.append(f"- Generated at: `{_now_iso()}`")
    if pytest_summary:
        lines.append(
            f"- Pytest Summary: **{pytest_summary.get('passed',0)}/{pytest_summary.get('total',0)} passed**, "
            f"failed={pytest_summary.get('failed',0)}"
        )
    if header_note:
        lines.append(f"- Context: {_md_escape(header_note)}")
    lines.append("")
    lines.append(f"**Verdict**: `{rv.verdict}`")
    lines.append("")
    lines.append("## Comments")
    if rv.comments:
        for c in rv.comments:
            lines.append(f"- {_md_escape(c)}")
    else:
        lines.append("- (no comments)")
    lines.append("")

    HAR_MD.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Patch writer & index
# ---------------------------------------------------------------------------
def _write_single_patch(seq: int, suggestion: PatchSuggestion) -> Optional[Path]:
    """
    1つの PatchSuggestion を .patch ファイルとして保存。
    - 連番 + スラッグ（file/function/時刻）で名称を作成
    - diff が空ならスキップ
    """
    diff_text = (suggestion.pseudo_diff or "").strip()
    if not diff_text:
        return None

    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    slug_core = _slugify(f"{suggestion.file}_{suggestion.function}")
    fname = f"{seq:04d}_{slug_core}_{ts}.patch"
    path = PATCHES_DIR / fname

    if not diff_text.endswith("\n"):
        diff_text += "\n"

    path.write_text(diff_text, encoding="utf-8")
    return path


def write_patch_files(out: InventorOutput) -> List[Tuple[Path, PatchSuggestion]]:
    """
    InventorOutput.patch_suggestions を .patch として保存し、[(path, suggestion), ...] を返す。
    """
    saved: List[Tuple[Path, PatchSuggestion]] = []
    if not out.patch_suggestions:
        return saved

    seq = _next_seq_num()
    for ps in out.patch_suggestions:
        p = _write_single_patch(seq, ps)
        if p:
            saved.append((p, ps))
            seq += 1
    return saved


def _write_single_patch_from_external(seq: int, title: str, file_path: str, patch_text: str) -> Optional[Path]:
    """
    外部 JSON アイテム（unified diff テキスト）から .patch を書き出す。
    """
    diff_text = (patch_text or "").strip()
    if not diff_text:
        return None
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    slug_core = _slugify(f"{file_path}_{title}") if title else _slugify(file_path)
    fname = f"{seq:04d}_{slug_core}_{ts}.patch"
    out = PATCHES_DIR / fname
    if not diff_text.endswith("\n"):
        diff_text += "\n"
    out.write_text(diff_text, encoding="utf-8")
    return out


def write_patches_index() -> None:
    """
    patches/ をスキャンして索引 Markdown を再生成（mtime 降順）。
    """
    items = _scan_patch_files()
    lines: List[str] = []
    lines.append("# Codex Patches Index")
    lines.append("")
    lines.append(f"- Generated at: `{_now_iso()}`")
    lines.append(f"- Total: **{len(items)}**")
    lines.append("")
    if not items:
        lines.append("_No patches yet._")
        PATCHES_INDEX.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.append("| File | Size | Modified |")
    lines.append("|------|------|----------|")
    for it in items:
        rel = it["rel"]
        name = it["name"]
        size = it["size"]
        mtime = it["mtime"].strftime("%Y-%m-%d %H:%M:%S %Z")
        lines.append(f"| [{name}]({rel}) | {size} | {mtime} |")

    lines.append("")
    PATCHES_INDEX.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# External suggestions support
# ---------------------------------------------------------------------------
def _load_external_suggestions() -> List[Dict[str, Any]]:
    """
    inventor_suggestions.json を読み込み（存在しなければ空配列）
    """
    if not INV_JSON.exists():
        return []
    try:
        return json.loads(INV_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []


def generate_patches_from_external() -> List[Tuple[Path, Dict[str, Any]]]:
    """
    外部 JSON から .patch を生成。
    - 'patch' があればそれを保存
    - 'before'/'after' があれば unified diff を生成して保存
    返り値: [(path, item), ...]
    """
    items = _load_external_suggestions()
    if not items:
        return []

    seq = _next_seq_num()
    saved: List[Tuple[Path, Dict[str, Any]]] = []

    for item in items:
        title = str(item.get("title") or "update")
        file_path = str(item.get("file") or "UNKNOWN")

        patch_text = ""
        if isinstance(item.get("patch"), str) and item["patch"].strip():
            patch_text = item["patch"]
        elif item.get("before") is not None and item.get("after") is not None:
            patch_text = _make_unified_diff_from_before_after(file_path, str(item["before"]), str(item["after"]))
        else:
            # 生成できない
            continue

        out_path = _write_single_patch_from_external(seq, title, file_path, patch_text)
        if out_path:
            saved.append((out_path, item))
            seq += 1

    return saved


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def _build_outputs_from_json(py_data: Dict[str, Any]) -> Tuple[InventorOutput, ReviewResult]:
    """
    tmp.json を解析して Inventor/Harmonia 出力を構築。
    - 失敗が無い場合は「軽い承認ムード」のノートを付与しつつ、既存レビュアルールは尊重。
    """
    pytest_result_for_inventor = build_pytest_result_for_inventor(py_data)
    inv = propose_fixes(pytest_result_for_inventor)
    rv = review(inv)
    return inv, rv


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    """
    - codex_reports/tmp.json を読み取り
    - Inventor 修正案 / Harmonia レビューを Markdown で生成
    - Inventor の pseudo_diff を .patch として保存し、パッチ索引を更新
    - 🆕 外部提案 inventor_suggestions.json があれば、それも .patch 生成
    - 失敗が無い場合も、空の提案と軽いコメントでファイルを出力（GUI 側で常に閲覧可能）
    - 🆕 pytest summary を pytest_summary.md に保存
    """
    header_note = None
    pytest_summary: Optional[Dict[str, int]] = None
    generated_patches: List[Tuple[Path, PatchSuggestion]] = []
    external_generated: List[Tuple[Path, Dict[str, Any]]] = []
    failed_tests: List[Dict[str, Any]] = []

    if not TMP_JSON.exists():
        # まだ小ループが走っていない等
        header_note = "No pytest JSON found. Skipped proposing fixes."
        empty_inv = InventorOutput(
            summary="No pytest result available.",
            root_causes=[],
            patch_suggestions=[],
            followup_tests=["pytest -q"],
        )
        rv = review(empty_inv)  # 既存レビューロジックに委ねる

        # pytest summary（空）も一応出力
        PYTEST_SUMMARY_MD.write_text(_render_pytest_summary_md({"passed": 0, "failed": 0, "total": 0}, []), encoding="utf-8")

        write_inventor_markdown(empty_inv, header_note=header_note, pytest_summary=None, generated_patches=None)
        write_harmonia_markdown(rv, header_note=header_note, pytest_summary=None)
        write_patches_index()  # 空でも再生成
        return 0

    # JSON 読込
    try:
        data = load_json(TMP_JSON)
    except Exception as e:
        header_note = f"Failed to load tmp.json: {e}"
        empty_inv = InventorOutput(
            summary="tmp.json could not be parsed.",
            root_causes=[str(e)],
            patch_suggestions=[],
            followup_tests=["pytest -q"],
        )
        rv = review(empty_inv)

        PYTEST_SUMMARY_MD.write_text(_render_pytest_summary_md({"passed": 0, "failed": 0, "total": 0}, []), encoding="utf-8")
        write_inventor_markdown(empty_inv, header_note=header_note, pytest_summary=None, generated_patches=None)
        write_harmonia_markdown(rv, header_note=header_note, pytest_summary=None)
        write_patches_index()
        return 0

    # 失敗の要約
    pytest_summary, failed_tests = _extract_summary_and_failed_tests(data)
    if pytest_summary.get("failed", 0) == 0:
        header_note = "All tests passed. Keeping suggestions minimal."

    # pytest サマリ MD を保存（GUIで表示）
    PYTEST_SUMMARY_MD.write_text(_render_pytest_summary_md(pytest_summary, failed_tests), encoding="utf-8")

    # Inventor/Harmonia 生成
    inv, rv = _build_outputs_from_json(data)

    # パッチ出力（内部）
    try:
        generated_patches = write_patch_files(inv)
    except Exception:
        generated_patches = []

    # パッチ出力（外部 JSON）
    try:
        external_generated = generate_patches_from_external()
    except Exception:
        external_generated = []

    # 出力
    write_inventor_markdown(
        inv,
        header_note=header_note,
        pytest_summary=pytest_summary,
        generated_patches=generated_patches if generated_patches else None,
        external_generated=external_generated if external_generated else None,
    )
    write_harmonia_markdown(rv, header_note=header_note, pytest_summary=pytest_summary)
    write_patches_index()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
