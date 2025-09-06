from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codex.run_codex_cycle import run_cycle, JSON_PATH, LATEST_MD

# レポジトリルート（…/noctria_kingdom）
REPO_ROOT = Path(__file__).resolve().parents[1]

# codex_reports 配下
REPORTS_DIR = JSON_PATH.parent
META_PATH = REPORTS_DIR / "mini_loop_meta.json"
CTXDIR = REPORTS_DIR / "context"
ALLOWED = CTXDIR / "allowed_files.txt"
TESTS_MAP = CTXDIR / "tests_map.json"


def load_allowed_tests() -> list[str]:
    """
    tests_map.json の "selected" を優先。
    なければ allowed_files.txt の stem をキーワードにして tests/**/*.py を拾う。
    最後まで空なら空リストを返す（= 全部対象）。
    """
    # 1) tests_map.json があれば使う
    if TESTS_MAP.exists():
        try:
            js = json.loads(TESTS_MAP.read_text(encoding="utf-8"))
            sel = js.get("selected") or []
            if sel:
                return sel
        except Exception:
            pass

    # 2) allowed_files.txt の stem から緩く拾う
    kws: list[str] = []
    if ALLOWED.exists():
        for ln in ALLOWED.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            stem = Path(ln).stem
            if len(stem) >= 3:
                kws.append(stem.lower())

    if kws:
        found: list[str] = []
        for p in (REPO_ROOT / "tests").rglob("test_*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            if any(kw in text for kw in kws):
                found.append(p.relative_to(REPO_ROOT).as_posix())
        if found:
            return found

    # 3) fallback: 空リスト → run_cycle 側で「デフォルト挙動」に任せる
    return []


def main() -> None:
    """
    小ループ実行:
      1) run_codex_cycle.run_cycle() で軽量テスト → codex_reports に Markdown/JSON を出力
      2) Inventor 提案 → Harmonia レビューを自動生成（静的Markdown）
      3) ループのメタ情報を mini_loop_meta.json に保存
    """
    # 事前に allowed_tests を決定
    allowed_tests = load_allowed_tests()
    pytest_args: str | None = None
    if allowed_tests:
        # pytest に渡すためスペース区切りの文字列に変換
        pytest_args = " ".join(allowed_tests)

    # 1) pytest 実行
    result, md_path = run_cycle(
        pytest_args=[],
        base_ref="",
        head_ref="",
        title="Mini Loop",
        enable_patch_notes=False,
    )

    # 2) Inventor → Harmonia の自然言語レビューを生成（ローカル静的版）
    try:
        subprocess.run(
            ["python", "-m", "codex.tools.review_pipeline"],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=False,
            text=True,
        )
    except Exception:
        # レビュー生成が失敗しても小ループ自体は継続
        pass

    # 3) メタ情報を保存（GUI側で軽く参照する用）
    meta = {
        "pytest": result.pytest,
        "git": result.git,
        "latest_md": str(md_path or LATEST_MD),
        "json_path": str(JSON_PATH),
        "allowed_tests": allowed_tests,
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
