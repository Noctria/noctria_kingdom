#!/usr/bin/env python3
# coding: utf-8

"""
⚔️ Veritas Strategy to EA Order Script (v2.1 Airflow再送対応)
- 評価され採用された戦略に基づき、EA（自動売買プログラム）が読み込む命令JSONファイルを生成する。
- Airflowから呼び出される。再送（--from-log）にも完全対応。
"""

import json
import importlib.util
import logging
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.core.path_config import STRATEGIES_DIR, VERITAS_ORDER_JSON, PDCA_LOG_DIR, VERITAS_EVAL_LOG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

def _load_simulate_function(filepath: Path):
    try:
        spec = importlib.util.spec_from_file_location("strategy_module", str(filepath))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, 'simulate'):
            raise AttributeError("指定された戦略モジュールにsimulate関数が存在しません。")
        return module.simulate
    except Exception as e:
        logging.error(f"戦略モジュールの読み込みに失敗しました: {filepath}, エラー: {e}", exc_info=True)
        raise

def _get_best_adopted_strategy() -> str:
    if not VERITAS_EVAL_LOG.exists():
        raise FileNotFoundError(f"評価ログが見つかりません: {VERITAS_EVAL_LOG}")
    with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
        results = json.load(f)
    passed_strategies = [r for r in results if r.get("passed")]
    if not passed_strategies:
        raise ValueError("採用基準を満たした戦略が存在しません。")
    best_strategy = max(passed_strategies, key=lambda r: r.get("final_capital", 0))
    return best_strategy.get("strategy")

def _save_order_and_log(signal_data: dict):
    # EA命令ファイル出力
    VERITAS_ORDER_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(VERITAS_ORDER_JSON, "w", encoding="utf-8") as f:
        json.dump(signal_data, f, indent=2, ensure_ascii=False)
    logging.info(f"✅ EAへの命令書を更新しました: {VERITAS_ORDER_JSON}")

    # PDCA履歴ログとして保存
    PDCA_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = signal_data["timestamp"].replace(":", "-").replace("T", "_")
    log_path = PDCA_LOG_DIR / f"order_{timestamp}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(signal_data, f, indent=2, ensure_ascii=False)
    logging.info(f"🗂️ PDCA履歴ログを保存しました: {log_path}")

def generate_order_from_log(log_path: Path):
    """
    PDCA履歴ログからそのまま命令JSONとPDCA履歴を復元
    """
    logging.info(f"🔁 ログ再送: {log_path}")
    if not log_path.exists():
        raise FileNotFoundError(f"指定されたPDCAログが見つかりません: {log_path}")
    with open(log_path, "r", encoding="utf-8") as f:
        signal_data = json.load(f)
    # 再送でも同じく命令書とPDCA履歴を保存
    _save_order_and_log(signal_data)
    logging.info("📜 ログ再送が完了しました。")

def main():
    """
    最良の採用戦略に基づき、EAへの命令JSONを生成する。
    """
    logging.info("⚔️ [Veritas] EA命令生成フェーズを開始します…")
    try:
        best_strategy_filename = _get_best_adopted_strategy()
        logging.info(f"最良の戦略として『{best_strategy_filename}』が選定されました。")
        strategy_path = STRATEGIES_DIR / "official" / best_strategy_filename
        if not strategy_path.exists():
            raise FileNotFoundError(f"公式戦略ファイルが見つかりません: {strategy_path}")
        simulate = _load_simulate_function(strategy_path)
        market_data = pd.DataFrame({'price': [150.0] * 100, 'RSI(14)': [60] * 100, 'spread': [1.5] * 100})
        result = simulate(market_data)
        signal = {
            "strategy": best_strategy_filename,
            "timestamp": datetime.now().isoformat(),
            "signal": result.get("signal", "BUY"),
            "symbol": result.get("symbol", "USDJPY"),
            "lot": result.get("lot", 0.1),
            "tp": result.get("tp", 10),
            "sl": result.get("sl", 8),
            "win_rate": result.get("win_rate"),
            "max_drawdown": result.get("max_drawdown"),
        }
        _save_order_and_log(signal)
        logging.info("📜 王国訓示:『この命、記されし記録として未来に残らん。』")
    except Exception as e:
        logging.error(f"EA命令の生成中に致命的なエラーが発生しました: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Veritas戦略からEA命令JSONを生成または再送するスクリプト")
    parser.add_argument("--from-log", type=str, help="再送用のPDCAログファイルパス")
    args = parser.parse_args()
    if args.from_log:
        generate_order_from_log(Path(args.from_log))
    else:
        main()
