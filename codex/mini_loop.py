# codex/mini_loop.py
from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
import json
import datetime as dt

# 既存の Codex Cycle を利用（JSON生成に使う）
from codex.run_codex_cycle import run_cycle, JSON_PATH, REPORTS_DIR, LATEST_MD  # type: ignore
from codex.agents.inventor import InventorScriptus  # type: ignore
from codex.agents.harmonia import HarmoniaOrdinis  # type: ignore


@dataclass
class MiniLoopReportPaths:
    inventor_md: Path
    harmonia_md: Path
    summary_md: Path


def _now_jst_iso() -> str:
    jst = dt.timezone(dt.timedelta(hours=9))
    return dt.datetime.now(tz=jst).isoformat(timespec="seconds")


def main(argv: list[str]) -> int:
    """
    小ループ（Lv1）
      1) pytest 実行（JSONのみ出力）
      2) 失敗ケース抽出
      3) Inventor: 修正案テキスト生成
      4) Harmonia: レビュー生成
      5) Markdown 保存
      6) 退出コード = 失敗数
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Codex Cycle 実行（Markdownはまだ不要）
    result, md = run_cycle(
        pytest_args=None,  # 簡単に最初はデフォルトで
        base_ref="HEAD~1",
        head_ref="HEAD",
        title="Noctria Codex Mini-Loop (Lv1)",
        enable_patch_notes=False,
    )
    # JSON を保存（run_cycle 側で tmp.json にも保存される想定）
    JSON_PATH.write_text(
        json.dumps(json.loads(json.dumps(result, default=str)), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2) 失敗ケース抽出
    failures = []
    for c in (result.pytest.cases or []):
        if c.outcome in ("failed", "error"):
            failures.append(
                {
                    "nodeid": c.nodeid,
                    "outcome": c.outcome,
                    "duration": c.duration,
                    "traceback": c.longrepr or "",
                }
            )

    # 3) Inventor: 修正案生成
    inventor = InventorScriptus()
    inventor_md = REPORTS_DIR / "inventor_suggestions.md"
    inventor_text = inventor.propose_fixes(
        failures=failures,
        context={
            "pytest_summary": {
                "total": result.pytest.total,
                "failed": result.pytest.failed,
                "errors": result.pytest.errors,
                "skipped": result.pytest.skipped,
                "duration_sec": result.pytest.duration_sec,
            },
            "git": {
                "branch": result.git.branch,
                "commit": result.git.commit,
                "dirty": result.git.is_dirty,
            },
            "generated_at": _now_jst_iso(),
        },
    )
    inventor_md.write_text(inventor_text, encoding="utf-8")

    # 4) Harmonia: レビュー生成
    harmonia = HarmoniaOrdinis()
    harmonia_md = REPORTS_DIR / "harmonia_review.md"
    harmonia_text = harmonia.review(
        failures=failures,
        inventor_suggestions=inventor_text,
        principles=[
            "小さく安全に直す（副作用最小化）",
            "テスト起点で因果を明確化（再現手順・期待値を伴う）",
            "GUI/PDCA/Observability の既存規約に準拠",
        ],
    )
    harmonia_md.write_text(harmonia_text, encoding="utf-8")

    # 5) まとめ（シンプルなランサマリーだけ）
    summary_md = REPORTS_DIR / "mini_loop_summary.md"
    summary_md.write_text(
        (
            f"# 🧪 Codex Mini-Loop (Lv1)\n\n"
            f"- Generated: `{_now_jst_iso()}`\n"
            f"- Pytest: total={result.pytest.total}, failed={result.pytest.failed}, errors={result.pytest.errors}, duration={result.pytest.duration_sec:.2f}s\n"
            f"- Inventor: {inventor_md.name}\n"
            f"- Harmonia: {harmonia_md.name}\n"
            f"- Latest Cycle: {LATEST_MD.name}\n"
        ),
        encoding="utf-8",
    )

    # 6) 退出コード（失敗数）
    return int((result.pytest.failed or 0) + (result.pytest.errors or 0))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
