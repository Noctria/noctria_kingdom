# airflow_docker/scripts/evaluate_generated_strategies.py

import os
import json
from datetime import datetime
from core.strategy_optimizer_adjusted import simulate_strategy_adjusted
from core.market_loader import load_market_data

def main():
    generated_dir = "/noctria_kingdom/strategies/veritas_generated"
    official_dir = "/noctria_kingdom/strategies/official"
    log_path = "/noctria_kingdom/airflow_docker/logs/veritas_eval_result.json"

    os.makedirs(official_dir, exist_ok=True)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    market_data = load_market_data("market_data.csv")

    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            eval_logs = json.load(f)
    else:
        eval_logs = []

    for filename in os.listdir(generated_dir):
        if not filename.endswith(".py"):
            continue

        path = os.path.join(generated_dir, filename)
        print(f"🔍 評価対象: {filename}")

        result = simulate_strategy_adjusted(path, market_data)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "filename": filename,
            "status": result.get("status", "error"),
            "final_capital": result.get("final_capital"),
            "win_rate": result.get("win_rate"),
            "max_drawdown": result.get("max_drawdown"),
            "total_trades": result.get("total_trades"),
            "error_message": result.get("error_message")
        }

        if result["status"] == "ok" and result["final_capital"] and result["final_capital"] >= 1_050_000:
            save_path = os.path.join(official_dir, filename)
            with open(path, "r") as src, open(save_path, "w") as dst:
                dst.write(src.read())
            print(f"✅ 採用: {filename}（資産 {result['final_capital']:,.0f}円）")
            log_entry["status"] = "adopted"
        elif result["status"] == "ok":
            print(f"❌ 不採用: {filename}（資産 {result['final_capital']:,.0f}円）")
            log_entry["status"] = "rejected"
        else:
            print(f"🚫 エラー: {filename} ➜ {result['error_message']}")

        eval_logs.append(log_entry)

    with open(log_path, "w") as f:
        json.dump(eval_logs, f, indent=2)

if __name__ == "__main__":
    main()
