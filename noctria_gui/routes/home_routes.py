from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from subprocess import run, PIPE
import json
from core.path_config import CATEGORY_MAP, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # ✅ dashboard.html 用の構造化された stats を渡す
    stats = {
        "filter": {
            "from": "",
            "to": "",
            "mode": "strategy",
            "sort": "score"
        },
        "promoted_count": 0,
        "pushed_count": 0,
        "active_strategy_count": 0,
        "tag_count": 0
    }
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats
    })


@router.get("/path-check", response_class=HTMLResponse)
async def path_check_form(request: Request):
    categories = list(CATEGORY_MAP.keys())
    return templates.TemplateResponse("path_checker.html", {
        "request": request,
        "categories": categories,
        "result": None
    })


@router.get("/path-check/run", response_class=HTMLResponse)
async def run_check(request: Request, category: str = "all", strict: bool = False):
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
            "stdout": proc.stdout.decode(),
            "stderr": proc.stderr.decode()
        }

    return templates.TemplateResponse("path_checker.html", {
        "request": request,
        "categories": list(CATEGORY_MAP.keys()),
        "selected_category": category,
        "strict": strict,
        "result": result_json
    })


@router.get("/api/check-paths")
async def check_paths_api(category: str = "all", strict: bool = False):
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
            "stdout": proc.stdout.decode(),
            "stderr": proc.stderr.decode()
        }
