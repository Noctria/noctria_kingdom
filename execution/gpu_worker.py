# gpu_worker.py
from fastapi import FastAPI
import subprocess
from datetime import datetime

app = FastAPI()

@app.get("/run-gpu-task")
def run_gpu_task():
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"gpu_task_log_{now}.txt"

    try:
        result = subprocess.run(
            ["python", "tensorflow_task.py"],
            capture_output=True,
            text=True
        )
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(result.stdout)
            f.write("\n--- stderr ---\n")
            f.write(result.stderr)

        return {
            "status": "success" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "log_file": log_file
        }

    except Exception as e:
        return {"status": "exception", "error": str(e)}
