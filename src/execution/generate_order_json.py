#!/usr/bin/env python3
# coding: utf-8

"""
⚔️ Veritas Strategy to EA Order Script (v2.0)
- 評価され採用された戦略に基づき、EA（自動売買プログラム）が読み込む命令JSONファイルを生成する。
- Airflowから呼び出されることを想定。
"""

import json
import importlib.util
import logging
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_configから必要な変数を正しくインポート
from src.core.path_config import STRATEGIES_DIR, VERITAS_ORDER_JSON, PDCA_LOG_DIR, VERITAS_EVAL_LOG

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


def _load_simulate_function(filepath: Path):
    """戦略ファイルからsimulate関数を動的に読み込む"""
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
    """評価ログから、最も成績の良い採用済み戦略のファイル名を取得する"""
    if not VERITAS_EVAL_LOG.exists():
        raise FileNotFoundError(f"評価ログが見つかりません: {VERITAS_EVAL_LOG}")
    
    with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    passed_strategies = [r for r in results if r.get("passed")]
    if not passed_strategies:
        raise ValueError("採用基準を満たした戦略が存在しません。")

    # 最終資産が最も高い戦略を最良とする
    best_strategy = max(passed_strategies, key=lambda r: r.get("final_capital", 0))
    return best_strategy.get("strategy")


def _save_order_and_log(signal_data: dict):
    """EAへの命令書とPDCA履歴ログの両方を保存する"""
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


def main():
    """
    Airflowから呼び出されるメイン関数。
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
        
        # NOTE: 本番運用では、実際の最新市場データを渡す
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

# ✅ CLI対応：--from-log 引数で再送可能
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Veritas戦略からEA命令JSONを生成または再送するスクリプト")
    parser.add_argument("--from-log", type=str, help="再送用のPDCAログファイルパス")
    args = parser.parse_args()

    if args.from_log:
        # generate_order_from_log(Path(args.from_log)) # この機能は必要に応じて実装
        logging.warning("ログからの再送機能は現在実装されていません。")
    else:
        main()
