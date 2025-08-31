# codex/mini_loop.py
from __future__ import annotations

import json
from pathlib import Path

from codex.run_codex_cycle import run_cycle, JSON_PATH, LATEST_MD

META_PATH = JSON_PATH.parent / "mini_loop_meta.json"


def main() -> None:
    # 小ループ実行（pytest_args=None なら軽量2本のみを run_codex_cycle 側で実行）
    result, md_path = run_cycle(
        pytest_args=None,
        base_ref="",
        head_ref="",
        title="Mini Loop",
        enable_patch_notes=False,
    )

    # ❌ ここで tmp.json を上書きしないこと！（run_codex_cycle が既に保存済み）
    # JSON_PATH.write_text(str(result), encoding="utf-8")  # ← これが元の原因

    # 代わりに、メタ情報が必要なら別ファイルへ保存（任意）
    meta = {"pytest": result.pytest, "git": result.git, "latest_md": md_path}
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # ついでに存在確認（デバッグ用、不要なら削除可）
    # print(f"Wrote meta: {META_PATH}")
    # print(f"Latest MD: {LATEST_MD}")


if __name__ == "__main__":
    main()
