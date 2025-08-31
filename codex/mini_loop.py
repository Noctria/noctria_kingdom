# codex/mini_loop.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codex.run_codex_cycle import run_cycle, JSON_PATH, LATEST_MD

# レポジトリルート（…/noctria_kingdom）
REPO_ROOT = Path(__file__).resolve().parents[1]

# codex_reports 配下
META_PATH = JSON_PATH.parent / "mini_loop_meta.json"


def main() -> None:
    """
    小ループ実行:
      1) run_codex_cycle.run_cycle() で軽量テスト → codex_reports に Markdown/JSON を出力
      2) 直後に Inventor 提案 → Harmonia レビューを自動生成（静的Markdown）
      3) ループのメタ情報を mini_loop_meta.json に保存
    """
    # 1) pytest 実行（軽量2本: pytest_args=None は run_codex_cycle 側で解釈）
    result, md_path = run_cycle(
        pytest_args=None,
        base_ref="",
        head_ref="",
        title="Mini Loop",
        enable_patch_notes=False,
    )

    # ❌ tmp.json を上書きしないこと！（run_codex_cycle が保存済み）
    # JSON_PATH.write_text(str(result), encoding="utf-8")  # これはやらない

    # 2) Inventor → Harmonia の自然言語レビューを生成（ローカル静的版）
    #    codex/tools/review_pipeline.py をサブプロセスで実行
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
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
