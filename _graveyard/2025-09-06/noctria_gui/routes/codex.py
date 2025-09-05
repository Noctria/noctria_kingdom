# noctria_gui/routes/codex.py
# -*- coding: utf-8 -*-
"""
🧪 Codex GUI Routes — v3.0
- GET  /codex           : HUDで Codex レビュー/パッチ状況を表示
- POST /codex/run       : codex.mini_loop を実行（pytest → tmp.json 生成）
- GET/POST /codex/review: codex.tools.review_pipeline を実行（MD & .patch & index 生成）

テンプレ側（codex.html）が参照するコンテキスト:
- page_title
- pytest_json            : tmp.json をロードした dict（なければ {}）
- pytest_summary_md      : codex_reports/pytest_summary.md の中身（文字列）
- inventor_md            : inventor_suggestions_render.md があればそれ、なければ inventor_suggestions.md
- harmonia_md            : harmonia_review.md の中身
- patches_index_md       : patches_index.md の中身
- patches                : [{"filename","size","relpath"}...] （codex_reports/patches/ 配下）
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "codex_reports"
REPORTS_DIR.mkdir(exist_ok=True, parents=True)

PATCHES_DIR = REPORTS_DIR / "patches"
PATCHES_DIR.mkdir(exist_ok=True, parents=True)

router = APIRouter(prefix="/codex", tags=["Codex"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_text_safe(path: Path, max_bytes: int = 800_000) -> str:
    """
    ファイルを最大 max_bytes まで読み込んで返す。存在しない場合は空文字。
    """
    try:
        if not path.exists():
            return ""
        b = path.read_bytes()
        if len(b) > max_bytes:
            return b[:max_bytes].decode("utf-8", errors="ignore") + "\n\n... (clipped)"
        return b.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"(read error: {e})"


def _load_json_safe(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _scan_patches() -> List[Dict[str, Any]]:
    """
    codex_reports/patches/ の .patch を列挙してメタ情報を返す。
    """
    items: List[Dict[str, Any]] = []
    for f in sorted(PATCHES_DIR.glob("*.patch")):
        try:
            stat = f.stat()
            items.append({
                "filename": f.name,
                "size": stat.st_size,
                "relpath": f"codex_reports/patches/{f.name}",
            })
        except Exception:
            continue
    return items


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@router.get("")
async def codex_home(request: Request) -> HTMLResponse:
    """
    Codex HUD ページ表示。
    """
    context: Dict[str, Any] = {
        "page_title": "🧪 Codex Mini-Loop",
        # JSON（pytest結果）
        "pytest_json": _load_json_safe(REPORTS_DIR / "tmp.json"),
        # MD 群
        "pytest_summary_md": _read_text_safe(REPORTS_DIR / "pytest_summary.md"),
        "inventor_md": (
            _read_text_safe(REPORTS_DIR / "inventor_suggestions_render.md")
            or _read_text_safe(REPORTS_DIR / "inventor_suggestions.md")
        ),
        "harmonia_md": _read_text_safe(REPORTS_DIR / "harmonia_review.md"),
        "patches_index_md": _read_text_safe(REPORTS_DIR / "patches_index.md"),
        # パッチ一覧
        "patches": _scan_patches(),
    }

    # 環境に合わせてテンプレ描画（app.state.render_template を採用）
    html = request.app.state.render_template(
        request,
        "codex.html",
        **context,
    )
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
@router.post("/run")
async def codex_run(request: Request, pytest_args: str = Form(default="")):
    """
    codex/mini_loop を実行。pytest 引数は現状未使用（mini_loop 側の既定を使用）。
    """
    cmd = ["python", "-m", "codex.mini_loop"]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        rc = proc.returncode
        request.session["toast"] = {
            "level": ("info" if rc == 0 else "warning"),
            "text": f"Codex Mini-Loop finished (exit={rc})",
        }
    except Exception as e:
        request.session["toast"] = {"level": "error", "text": f"Exec failed: {e}"}
    return RedirectResponse(url="/codex", status_code=303)


# ========= レビュー実行エンドポイント（GET/POST 両対応） =========
async def _run_review(request: Request) -> RedirectResponse:
    """
    codex/tools/review_pipeline を実行して Markdown / .patch / index を更新し、/codex に戻す。
    """
    cmd = ["python", "-m", "codex.tools.review_pipeline"]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        rc = proc.returncode
        request.session["toast"] = {
            "level": ("info" if rc == 0 else "warning"),
            "text": f"Review pipeline finished (exit={rc})",
        }
    except Exception as e:
        request.session["toast"] = {"level": "error", "text": f"Review failed: {e}"}
    return RedirectResponse(url="/codex", status_code=303)


@router.get("/review")
async def codex_review_get(request: Request):
    # ブラウザ直叩きに対応
    return await _run_review(request)


@router.post("/review")
async def codex_review_post(request: Request):
    # フォームボタンからの POST に対応
    return await _run_review(request)
