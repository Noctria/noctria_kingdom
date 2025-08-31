# noctria_gui/routes/codex.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
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


def _web_url(p: Optional[Path]) -> Optional[str]:
    """
    StaticFiles('/codex_reports' -> CODEX_DIR) で配信しているため、
    ブラウザからは /codex_reports/<filename> を叩く必要がある。
    """
    if isinstance(p, Path):
        return f"/codex_reports/{p.name}"
    return None


# ------------------------------------------------------------
# JSONレポート（pytest結果）のパース
# ------------------------------------------------------------
def _parse_json_report(path: Path) -> List[Dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tests = data.get("tests", [])
        rows = []
        for t in tests:
            rows.append(
                {
                    "nodeid": t.get("nodeid"),
                    "outcome": t.get("outcome"),
                    "duration": round(t.get("call", {}).get("duration", 0), 4),
                }
            )
        return rows
    except Exception:
        return []


def _read_tail(path: Path, lines: int = 80) -> str:
    try:
        txt = path.read_text(encoding="utf-8")
        arr = txt.splitlines()
        return "\n".join(arr[-lines:])
    except Exception as e:
        return f"(read error: {e})"


# ------------------------------------------------------------
# Codex Home
# ------------------------------------------------------------
@router.get("")
async def codex_home(request: Request) -> HTMLResponse:
    reports = _scan_reports()

    # プレビュー（tail）
    previews: Dict[str, str] = {
        k: (_read_tail(p, 120) if isinstance(p, Path) else "(not found)")
        for k, p in reports.items()
    }

    # pytest結果のテーブル
    tests_table: List[Dict] = []
    if reports.get("tmp_json"):
        tests_table = _parse_json_report(reports["tmp_json"])  # type: ignore[arg-type]

    # 🔗 ブラウザ用の配信URL（/codex_reports/<filename>）
    links: Dict[str, Optional[str]] = {k: _web_url(p) for k, p in reports.items()}

    html = request.app.state.render_template(
        request,
        "codex.html",
        page_title="🧪 Codex Mini-Loop",
        # 既存のファイルパス（サーバ側で読む用）
        reports={k: (str(v) if isinstance(v, Path) else None) for k, v in reports.items()},
        # ブラウザが開くべきURL
        links=links,
        previews=previews,
        tests_table=tests_table,
    )
    return HTMLResponse(html)


# ------------------------------------------------------------
# Codex Run
# ------------------------------------------------------------
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
