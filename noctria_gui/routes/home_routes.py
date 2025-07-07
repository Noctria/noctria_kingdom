from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from subprocess import run, PIPE
from core.path_config import CATEGORY_MAP, NOCTRIA_GUI_TEMPLATES_DIR

import json
from typing import Any

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    # dashboard.html に必要な構造を初期化
    stats = {
        "promoted_count": 0,
        "pushed_count": 0,
        "avg_win_rate": 0.0,
        "filter": {"from": "", "to": ""},
        "dates": [],
        "daily_scores": [],
        "promoted_values": [],
        "pushed_values": [],
        "win_rate_values": [],
        "avg_win_rates": [],
        "avg_max_dds": [],
    }
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
    })


@router.get("/path-check", response_class=HTMLResponse)
async def path_check_form(request: Request) -> HTMLResponse:
    categories = list(CATEGORY_MAP.keys())
    return templates.TemplateResponse("path_checker.html", {
        "request": request,
        "categories": categories,
        "result": None
    })


@router.get("/path-check/run", response_class=HTMLResponse)
async def run_check(
    request: Request, category: str = "all", strict: bool = False
) -> HTMLResponse:
    command = ["python3", "tools/verify_path_config.py", "--json"]
    if category != "all":
        command += ["--category", category]
    if strict:
        command += ["--strict"]

    proc = run(command, stdout=PIPE, stderr=PIPE)
    try:
        result_json = json.loads(proc.stdout.decode())
    except json.JSONDecodeError:
        result_json = {
            "success": False,
            "error": "JSON decode failed",
            "stdout": proc.stdout.decode(errors="ignore"),
            "stderr": proc.stderr.decode(errors="ignore"),
        }

    return templates.TemplateResponse("path_checker.html", {
        "request": request,
        "categories": list(CATEGORY_MAP.keys()),
        "selected_category": category,
        "strict": strict,
        "result": result_json,
    })


@router.get("/api/check-paths", response_class=JSONResponse)
async def check_paths_api(
    category: str = "all", strict: bool = False
) -> Any:
    command = ["python3", "tools/verify_path_config.py", "--json"]
    if category != "all":
        command += ["--category", category]
    if strict:
        command += ["--strict"]

    proc = run(command, stdout=PIPE, stderr=PIPE)
    try:
        result_json = json.loads(proc.stdout.decode())
        return result_json
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "JSON decode failed",
            "stdout": proc.stdout.decode(errors="ignore"),
            "stderr": proc.stderr.decode(errors="ignore"),
        }
