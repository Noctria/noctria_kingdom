@echo off
cd /d %~dp0
echo 🚀 FastAPI GPU Worker を起動中...
uvicorn gpu_worker:app --host 0.0.0.0 --port 8000 --reload
pause
