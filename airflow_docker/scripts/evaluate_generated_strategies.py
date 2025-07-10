# airflow_docker/scripts/evaluate_generated_strategies.py

import os
import json
import subprocess
from datetime import datetime
from core.strategy_optimizer_adjusted import simulate_strategy_adjusted
from core.market_loader import load_market_data
from core.path_config import STRATEGIES_DIR, LOGS_DIR, PROJECT_ROOT

def evaluate_strategy(strategy_filename: str, market_csv: str = "market_data.csv") -> dict:
    """
    戦略ファイル（.py）を受け取り、評価と採用処理を実施。
    - 成功時: 採用してGitHub Pushまで実行
    - 失敗時: エラー内容をログ
    """
    generated_path = STRATEGIES_DIR / "veritas_generated" / strategy_filename
    official_path = STRATEGIES_DIR / "official" / strategy_filename
    log_path = LOGS_DIR / "veritas_eval_result.json"

    market_data = load_market_data(market_csv)

    if not generated_path.exists():
        return {"status": "error", "error_message": f"{strategy_filename} が存在しません"}

    print(f"🔍 評価中: {strategy_filename}")
    result = simulate_strategy_adjusted(str(generated_path), market_data)

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "filename": strategy_filename,
        "status": result.get("status", "error"),
        "final_capital": result.get("final_capital"),
        "win_rate": result.get("win_rate"),
        "max_drawdown": result.get("max_drawdown"),
        "total_trades": result.get("total_trades"),
        "error_message": result.get("error_message")
    }

    try:
        if result["status"] == "ok" and result.get("final_capital", 0) >= 1_050_000:
            # ✅ 採用
            with open(generated_path, "r") as src, open(official_path, "w") as dst:
                dst.write(src.read())
            print(f"✅ 採用: {strategy_filename}（資産 {result['final_capital']:,.0f}円）")
            log_entry["status"] = "adopted"

            try:
                subprocess.run(["git", "add", str(official_path)], cwd=str(PROJECT_ROOT), check=True)
                subprocess.run(["git", "commit", "-m", f"✅ Adopt strategy: {strategy_filename}"], cwd=str(PROJECT_ROOT), check=True)
                subprocess.run(["git", "push"], cwd=str(PROJECT_ROOT), check=True)
                print(f"🚀 GitHubへPush完了: {strategy_filename}")
                log_entry["git_push"] = "success"
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Git操作失敗: {e}")
                log_entry["git_push"] = "failed"

        elif result["status"] == "ok":
            print(f"❌ 不採用: {strategy_filename}（資産 {result['final_capital']:,.0f}円）")
            log_entry["status"] = "rejected"
        else:
            print(f"🚫 評価エラー: {strategy_filename} ➜ {result['error_message']}")

    except Exception as e:
        log_entry["status"] = "error"
        log_entry["error_message"] = str(e)

    # 🔽 評価ログの追記保存
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        if log_path.exists():
            with open(log_path, "r") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)
        with open(log_path, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"⚠️ ログ保存失敗: {e}")

    return log_entry


if __name__ == "__main__":
    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    if not filename:
        print("📛 戦略ファイル名が必要です: python evaluate_generated_strategies.py strategy_xxx.py")
        exit(1)

    result = evaluate_strategy(filename)
    print(json.dumps(result, indent=2, ensure_ascii=False))
