import shutil
from pathlib import Path
import subprocess
from datetime import datetime

# 保存パス設定
STRATEGY_DIR = Path("strategies/official/")
SCRIPT_EVAL = Path("veritas/evaluate_veritas.py")
SCRIPT_DO = Path("execution/generate_order_json.py")
UPLOAD_LOG_DIR = Path("logs/uploads")

async def process_uploaded_strategy(file) -> str:
    try:
        # === 保存ディレクトリ作成（日時ベース） ===
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = UPLOAD_LOG_DIR / timestamp
        save_dir.mkdir(parents=True, exist_ok=True)

        # === アップロードファイル保存 ===
        dest_path = save_dir / file.filename
        with dest_path.open("wb") as f:
            content = await file.read()
            f.write(content)

        # === strategies/official/ にも一時配置（評価対象として）
        official_path = STRATEGY_DIR / file.filename
        shutil.copy(dest_path, official_path)

        # === 評価スクリプト実行 ===
        eval_proc = subprocess.run(
            ["python", str(SCRIPT_EVAL)],
            capture_output=True,
            text=True
        )

        # === ログ保存 ===
        result_log = save_dir / "upload_result.txt"
        result_text = eval_proc.stdout

        # === 採用があれば命令生成 ===
        if "採用基準を満たした戦略数: 0" not in eval_proc.stdout:
            do_proc = subprocess.run(
                ["python", str(SCRIPT_DO)],
                capture_output=True,
                text=True
            )
            result_text += "\n\n" + do_proc.stdout
        else:
            result_text += "\n❌ 採用なし"

        result_log.write_text(result_text, encoding="utf-8")
        return f"✅ 保存: {file.filename}\n📁 ログ: {result_log}\n\n" + result_text

    except Exception as e:
        return f"❌ エラー: {str(e)}"
