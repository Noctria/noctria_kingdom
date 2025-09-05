# src/execution/simulate_official_strategy.py

import os
import importlib.util
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# --- 王国の中枢モジュールをインポート ---
from core.path_config import STRATEGIES_DIR, MARKET_DATA_CSV, LOGS_DIR
from core.logger import setup_logger
from core.risk_control import RiskControl

# --- 訓練場の記録係をセットアップ ---
log_dir = LOGS_DIR / "simulations"
log_dir.mkdir(parents=True, exist_ok=True)
logger = setup_logger("OfficialStrategySimulator", log_dir / "simulation.log")


def load_official_strategies():
    """`strategies/official`ディレクトリから全ての戦略クラスを動的にロードする"""
    strategies = {}
    official_dir = STRATEGIES_DIR / "official"
    if not official_dir.exists():
        logger.warning(f"⚠️ 公式戦略ディレクトリが存在しません: {official_dir}")
        return strategies

    for fname in os.listdir(official_dir):
        if fname.endswith(".py") and not fname.startswith("__"):
            strategy_name = os.path.splitext(fname)[0]
            strategy_path = official_dir / fname
            try:
                spec = importlib.util.spec_from_file_location(strategy_name, strategy_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # クラス名がキャメルケース（例: PrometheusOracle）であることを想定
                class_name = "".join(word.capitalize() for word in strategy_name.split('_'))
                if hasattr(module, class_name):
                    strategies[strategy_name] = getattr(module, class_name)()
                    logger.info(f"✅ 戦略をロードしました: {class_name}")
            except Exception as e:
                logger.error(f"❌ 戦略ファイルのロードに失敗: {fname}, エラー: {e}", exc_info=True)
    return strategies


class Backtester:
    """
    公式戦略のバックテストを実行し、パフォーマンスを評価するクラス
    """
    def __init__(self, data: pd.DataFrame, strategies: dict, initial_capital: float = 100000.0, transaction_cost_pct: float = 0.0005):
        self.data = data
        self.strategies = strategies
        self.initial_capital = initial_capital
        self.transaction_cost_pct = transaction_cost_pct
        self.risk_control = RiskControl(initial_capital)

    def run(self):
        """シミュレーションのメインループを実行する"""
        logger.info(f"🚀 バックテストを開始します。対象戦略: {list(self.strategies.keys())}")
        
        capital = self.initial_capital
        position = 0  # 0: No position, 1: Long, -1: Short
        equity_curve = [initial_capital]

        for i in range(1, len(self.data)):
            current_state = self.data.iloc[i]
            current_price = current_state['close']
            
            # --- 1. 各戦略から判断を取得 ---
            # ここでは単純な多数決とするが、MetaAIを組み込むことも可能
            decisions = []
            for name, strategy in self.strategies.items():
                # 戦略のprocessメソッドが存在すると仮定
                if hasattr(strategy, 'process'):
                    # 実際のprocessメソッドの引数に合わせて要調整
                    decision = strategy.process(current_state.to_dict()) 
                    decisions.append(decision.get('action', 'hold'))

            # 多数決で最終判断
            final_decision = max(set(decisions), key=decisions.count) if decisions else 'hold'

            # --- 2. リスクチェックと取引実行 ---
            is_ok, reason = self.risk_control.pre_trade_check(new_trade_size=1.0, current_time=current_state.name)
            if not is_ok:
                logger.warning(f"🚨 取引停止: {reason} (at {current_state.name})")
                if position != 0: # ポジションがあればクローズ
                    final_decision = 'close'
                else:
                    final_decision = 'hold'

            # --- 3. ポジション管理と損益計算 ---
            pnl = 0
            if final_decision == 'buy' and position <= 0:
                position = 1
                capital -= capital * self.transaction_cost_pct
            elif final_decision == 'sell' and position >= 0:
                position = -1
                capital -= capital * self.transaction_cost_pct
            elif final_decision == 'close' and position != 0:
                position = 0
            
            if position != 0:
                price_change = current_price - self.data['close'].iloc[i-1]
                pnl = price_change * position
            
            capital += pnl
            equity_curve.append(capital)
            
            # リスク管理モジュールに結果を反映
            self.risk_control.update_trade_result(pnl, trade_size=1.0, trade_time=current_state.name)

        return pd.Series(equity_curve, index=self.data.index)

    @staticmethod
    def calculate_metrics(equity_curve: pd.Series):
        """パフォーマンス指標を計算する"""
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        daily_returns = equity_curve.pct_change().dropna()
        
        sharpe_ratio = 0
        if daily_returns.std() != 0:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

        cumulative_max = equity_curve.cummax()
        drawdown = (equity_curve - cumulative_max) / cumulative_max
        max_drawdown = drawdown.min()

        return {
            "total_return_pct": total_return * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": max_drawdown * 100,
            "final_equity": equity_curve.iloc[-1]
        }

    @staticmethod
    def generate_report(equity_curve: pd.Series, metrics: dict, report_path: Path):
        """結果をプロットし、レポートを保存する"""
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(15, 7))
        equity_curve.plot(ax=ax, title='Strategy Equity Curve', lw=2)
        ax.set_ylabel('Equity')
        ax.set_xlabel('Date')
        
        report_text = "\n".join([f"{k}: {v:.4f}" for k, v in metrics.items()])
        ax.text(0.02, 0.95, report_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5))
        
        plot_path = report_path.with_suffix('.png')
        fig.savefig(plot_path)
        logger.info(f"📊 パフォーマンスグラフを保存しました: {plot_path}")
        
        with open(report_path.with_suffix('.json'), 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"📋 パフォーマンスレポートを保存しました: {report_path.with_suffix('.json')}")


def main():
    """
    このスクリプトのメイン処理（Airflow DAGから呼び出される）
    """
    logger.info("="*50)
    logger.info("🏰 王国の公式戦略シミュレーションを開始します...")
    logger.info("="*50)

    # 1. データのロード
    try:
        market_data = pd.read_csv(MARKET_DATA_CSV, index_col='datetime', parse_dates=True)
        logger.info(f"💾 市場データをロードしました。期間: {market_data.index.min()} ~ {market_data.index.max()}")
    except FileNotFoundError:
        logger.error(f"❌ 市場データファイルが見つかりません: {MARKET_DATA_CSV}")
        return

    # 2. 戦略のロード
    strategies = load_official_strategies()
    if not strategies:
        logger.warning("⚠️ 実行対象の公式戦略がありません。処理を終了します。")
        return

    # 3. バックテストの実行
    backtester = Backtester(data=market_data, strategies=strategies)
    equity_curve = backtester.run()

    # 4. パフォーマンス評価とレポート生成
    metrics = Backtester.calculate_metrics(equity_curve)
    logger.info(f"🏆 シミュレーション結果: {metrics}")
    
    report_file_path = log_dir / f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    Backtester.generate_report(equity_curve, metrics, report_file_path)

    logger.info("✅ 全てのシミュレーションプロセスが完了しました。")


if __name__ == "__main__":
    main()
