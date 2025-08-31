# noctria_gui/routes/codex.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse

ROOT = Path(__file__).resolve().parents[2]
CODEX_DIR = ROOT / "codex_reports"
CODEX_DIR.mkdir(exist_ok=True, parents=True)

router = APIRouter(prefix="/codex", tags=["Codex"])


def _scan_reports() -> Dict[str, Optional[str]]:
    """
    codex_reports 下の既知ファイルをスキャンし、存在すれば
    /codex_reports/xxx の形で返す。
    """
    def pick(name: str) -> Optional[str]:
        p = CODEX_DIR / name
        return f"/codex_reports/{name}" if p.exists() else None

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
async def codex_home(request: Request) -> HTMLResponse:
    reports = _scan_reports()

    # previews 用は実ファイルパスで読む必要あり
    previews: Dict[str, str] = {}
    for k, webpath in reports.items():
        if webpath:
            fname = webpath.replace("/codex_reports/", "")
            fpath = CODEX_DIR / fname
            previews[k] = _read_tail(fpath, 120)
        else:
            previews[k] = "(not found)"

    html = request.app.state.render_template(
        request,
        "codex.html",
        page_title="🧪 Codex Mini-Loop",
        reports=reports,
        previews=previews,
    )
    return HTMLResponse(html)


@router.post("/run")
async def codex_run(request: Request, pytest_args: str = Form(default="")):
    """
    codex/mini_loop をサブプロセスで実行。
    pytest_args は未使用だが将来引数に渡す想定。
    """
    cmd = ["python", "-m", "codex.mini_loop"]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        rc = proc.returncode
        request.session["toast"] = {
            "level": "info" if rc == 0 else "warning",
            "text": f"Codex Mini-Loop finished (exit={rc})",
        }
    except Exception as e:
        request.session["toast"] = {"level": "error", "text": f"Exec failed: {e}"}
    return RedirectResponse(url="/codex", status_code=303)
