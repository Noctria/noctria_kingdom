# noctria_gui/routes/codex.py
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse

ROOT = Path(__file__).resolve().parents[2]
CODEX_DIR = ROOT / "codex_reports"
CODEX_DIR.mkdir(exist_ok=True, parents=True)

router = APIRouter(prefix="/codex", tags=["Codex"])


# ------------------------------------------------------------
# レポートスキャン
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# pytest JSON 結果をロードしてテーブル化
# ------------------------------------------------------------
def _load_tests_from_json(path: Path) -> tuple[list[Dict[str, Any]], Dict[str, int]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], {}

    tests = []
    passed = failed = 0
    for t in data.get("tests", []):
        nodeid = t.get("nodeid")
        outcome = t.get("outcome")
        duration = None
        if "call" in t and isinstance(t["call"], dict):
            duration = t["call"].get("duration")

        tests.append({
            "nodeid": nodeid,
            "outcome": outcome,
            "duration": duration,
        })

        if outcome == "passed":
            passed += 1
        elif outcome == "failed":
            failed += 1

    summary = {
        "passed": passed,
        "failed": failed,
        "total": len(tests),
    }
    return tests, summary


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@router.get("")
async def codex_home(request: Request) -> HTMLResponse:
    reports = _scan_reports()
    previews: Dict[str, str] = {
        k: (_read_tail(p, 120) if isinstance(p, Path) else "(not found)")
        for k, p in reports.items()
    }

    # pytest JSON 結果
    tests_table: list[Dict[str, Any]] = []
    tests_summary: Dict[str, int] = {}
    if reports.get("tmp_json"):
        tests_table, tests_summary = _load_tests_from_json(reports["tmp_json"])

    html = request.app.state.render_template(
        request,
        "codex.html",
        page_title="🧪 Codex Mini-Loop",
        reports={k: (str(v) if isinstance(v, Path) else None) for k, v in reports.items()},
        links={k: ("/codex_reports/" + v.name if isinstance(v, Path) else None) for k, v in reports.items()},
        previews=previews,
        tests_table=tests_table,
        tests_summary=tests_summary,
    )
    return HTMLResponse(html)


@router.post("/run")
async def codex_run(request: Request, pytest_args: str = Form(default="")):
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
