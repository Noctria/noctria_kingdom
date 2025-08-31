# noctria_gui/routes/codex.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List

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


def _load_tmp_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path or not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_pytest_results(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """tmp.json から summary と tests を抽出。summary に failed を補完。"""
    summary = dict(data.get("summary") or {})
    passed = int(summary.get("passed") or 0)
    total = int(summary.get("total") or summary.get("collected") or 0)
    failed = max(0, total - passed)
    summary_out = {"passed": passed, "failed": failed, "total": total}

    tests = data.get("tests") or []
    # tests 各要素の call.duration を安全に参照できるよう補正
    for t in tests:
        call = t.get("call") or {}
        dur = call.get("duration", 0.0) if isinstance(call, dict) else 0.0
        t["call"] = {"duration": float(dur)}
    return summary_out, tests


@router.get("")
async def codex_home(request: Request) -> HTMLResponse:
    reports = _scan_reports()
    previews: Dict[str, str] = {
        k: (_read_tail(p, 120) if isinstance(p, Path) else "(not found)") for k, p in reports.items()
    }

    # tmp.json を読み込んで pytest サマリーと明細を作る
    pytest_summary = None
    pytest_tests: List[Dict[str, Any]] = []
    data = _load_tmp_json(reports.get("tmp_json"))
    if data:
        pytest_summary, pytest_tests = _extract_pytest_results(data)

    html = request.app.state.render_template(
        request,
        "codex.html",
        page_title="🧪 Codex Mini-Loop",
        reports={k: (str(v) if isinstance(v, Path) else None) for k, v in reports.items()},
        previews=previews,
        pytest_summary=pytest_summary,
        pytest_tests=pytest_tests,
    )
    return HTMLResponse(html)


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


# ========= ここから: レビュー実行エンドポイント（GET/POST 両対応） =========

async def _run_review(request: Request) -> RedirectResponse:
    """
    codex/tools/review_pipeline を実行して Markdown 出力を更新し、/codex に戻す。
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
