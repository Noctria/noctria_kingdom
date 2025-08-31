# noctria_gui/routes/codex.py
# -*- coding: utf-8 -*-
"""
🔧 Codex HUD — Mini-Loop 実行＆レポート閲覧

提供:
- GET  /codex          : レポート一覧＆実行UI
- POST /codex/run      : mini_loop を実行（subprocess）
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

# 既存プロジェクトのルート推定（noctria_kingdom 直下想定）
ROOT = Path(__file__).resolve().parents[2]
CODEX_DIR = ROOT / "codex_reports"
CODEX_DIR.mkdir(exist_ok=True, parents=True)

router = APIRouter(prefix="/codex", tags=["Codex"])

def _scan_reports() -> Dict[str, Path | None]:
    def pick(name: str) -> Path | None:
        p = CODEX_DIR / name
        return p if p.exists() else None

    return {
        "latest_cycle": pick("latest_codex_cycle.md"),
        "tmp_json": pick("tmp.json"),
        "inventor": pick("inventor_suggestions.md"),
        "harmonia": pick("harmonia_review.md"),
        "mini_summary": pick("mini_loop_summary.md"),
    }

def _read_tail(path: Path, lines: int = 80) -> str:
    try:
        txt = path.read_text(encoding="utf-8")
        arr = txt.splitlines()
        return "\n".join(arr[-lines:])
    except Exception as e:
        return f"(read error: {e})"

@router.get("")
async def codex_home(request: Request, templates: Jinja2Templates = Depends(lambda: request.app.state.jinja_env)):
    reports = _scan_reports()
    previews: Dict[str, str] = {}
    for k, p in reports.items():
        if isinstance(p, Path):
            previews[k] = _read_tail(p, 120)
        else:
            previews[k] = "(not found)"
    return templates.TemplateResponse(
        "codex.html",
        {
            "request": request,
            "page_title": "🧪 Codex Mini-Loop",
            "reports": {k: str(v) if isinstance(v, Path) else None for k, v in reports.items()},
            "previews": previews,
        },
    )

@router.post("/run")
async def codex_run(request: Request, pytest_args: str = Form(default="-q")):
    """
    codex/mini_loop を実行。pytest 引数は任意（既定 -q）。
    """
    cmd = ["python", "-m", "codex.mini_loop"]
    # mini_loop 側で pytest_args を扱いたい場合は環境変数／引数へ
    env = dict(**dict(Path, **{}))  # dummy to ensure isolation on some envs
    try:
        # 直下ルートで実行（ROOT）
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=None)
        rc = proc.returncode
        # Flash 的な簡易メッセージ（セッショントーストがあればそこへ統合）
        msg = f"Codex Mini-Loop finished (exit={rc})"
        request.session.setdefault("toasts", []).append({"level": "info" if rc == 0 else "warning", "text": msg})
    except Exception as e:
        request.session.setdefault("toasts", []).append({"level": "error", "text": f"Exec failed: {e}"})
    return RedirectResponse(url="/codex", status_code=303)
