from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from subprocess import run, PIPE
import json
from core.path_config import CATEGORY_MAP

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")

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
        return JSONResponse(status_code=200, content=result_json)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "JSON decode failed",
                "stdout": proc.stdout.decode(),
                "stderr": proc.stderr.decode()
            }
        )
