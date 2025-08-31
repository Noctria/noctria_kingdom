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

def _scan_reports() -> Dict[str, Optional[Path]]:
    def pick(name: str) -> Optional[Path]:
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
async def codex_home(request: Request) -> HTMLResponse:
    reports = _scan_reports()
    previews: Dict[str, str] = {k: (_read_tail(p, 120) if isinstance(p, Path) else "(not found)") for k, p in reports.items()}
    html = request.app.state.render_template(
        request,
        "codex.html",
        page_title="🧪 Codex Mini-Loop",
        reports={k: (str(v) if isinstance(v, Path) else None) for k, v in reports.items()},
        previews=previews,
    )
    return HTMLResponse(html)

@router.post("/run")
async def codex_run(request: Request, pytest_args: str = Form(default="")):
    cmd = ["python", "-m", "codex.mini_loop"]
    # いまは mini_loop 側が既定ターゲットを持つ想定。pytest_args を後で渡すなら環境変数や引数拡張へ。
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        rc = proc.returncode
        request.session["toast"] = {"level": ("info" if rc == 0 else "warning"), "text": f"Codex Mini-Loop finished (exit={rc})"}
    except Exception as e:
        request.session["toast"] = {"level": "error", "text": f"Exec failed: {e}"}
    return RedirectResponse(url="/codex", status_code=303)
