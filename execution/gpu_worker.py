from fastapi import FastAPI
import subprocess

app = FastAPI()

@app.get("/")
def root():
    return {"message": "FastAPI サーバー動作中 ✅"}

@app.get("/run-gpu-task")
def run_gpu_task():
    try:
        # GPU処理用のスクリプトを呼び出す（ファイル名は必要に応じて変更）
        result = subprocess.run(
            ["python", "your_tensorflow_script.py"],  # ← 実際のスクリプト名に置き換えてください
            capture_output=True,
            text=True,
            check=True  # エラーがあれば例外を発生
        )
        return {"output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {
            "error": "スクリプト実行中にエラーが発生しました",
            "stderr": e.stderr
        }
