# strategy_optimizer_adjusted.py
import numpy as np
import pandas as pd
from risk_control import RiskControl

def load_market_data(csv_file='market_data.csv'):
    """
    CSVファイルから市場データを読み込み、日次終値のNumPy配列を返します。
    CSVファイルには、'Date' と 'Close' のカラムが必要です。
    """
    try:
        df = pd.read_csv(csv_file, parse_dates=['Date'])
        df.sort_values('Date', inplace=True)
        prices = df['Close'].values
        print(f"CSVから{len(prices)}件の価格データを取得しました。")
        return prices
    except Exception as e:
        print("CSVの読み込みに失敗しました:", e)
        return None

def simulate_strategy_adjusted(prices, entry_threshold, exit_threshold, initial_capital=1000000):
    """
    リスク管理モジュール（RiskControl）を統合したシンプルなロング戦略のシミュレーションです。
    
    パラメータ:
      prices          : 過去の価格データ（1次元のNumPy配列）。
      entry_threshold : エントリー閾値（下落率、例: 0.02は2%の下落）。
      exit_threshold  : エグジット閾値（上昇率、例: 0.02は2%の上昇）。
      initial_capital : 初期資本金（例: 1,000,000 円）。
      
    戻り値:
      リスク管理ルールに基づき得られた最終的な資本金。
      ※リスク閾値に達して早期決済となった場合、その時点の資本金が返されます。
    """
    risk_control = RiskControl(initial_capital)
    position = 0       # 0: 未ポジション, 1: ロングポジション
    shares = 0         # 保有株数（または通貨単位）
    buy_price = None   # エントリー時の価格

    for i in range(1, len(prices)):
        # 毎日の始めにリスク状況をチェック
        _, _, active = risk_control.check_risk()
        if not active:
            print(f"【警告】リスク制御によりシミュレーション終了 (Day {i})")
            return risk_control.current_capital

        # 前日比の日次リターンを計算
        daily_return = (prices[i] - prices[i-1]) / prices[i-1]

        # エントリー判断: 未ポジションかつ当日のリターンがエントリー閾値以下なら買い
        if position == 0 and daily_return <= -entry_threshold:
            shares = risk_control.current_capital / prices[i]
            buy_price = prices[i]
            position = 1
            # ログ出力（必要に応じてコメントアウト解除）
            # print(f"エントリー: Day {i}, Price {prices[i]:.2f}")
        
        # エグジット判断: ポジションを保有中かつ日次リターンがエグジット閾値以上なら売り
        elif position == 1 and daily_return >= exit_threshold:
            sell_value = shares * prices[i]
            profit_loss = sell_value - (shares * buy_price)
            risk_control.update_account(profit_loss)  # 資本金を更新
            position = 0
            shares = 0
            buy_price = None
            # print(f"エグジット: Day {i}, Price {prices[i]:.2f}, P/L: {profit_loss:.2f}")

    # シミュレーション終了時に、まだポジションが残っていれば決済
    if position == 1:
        sell_value = shares * prices[-1]
        profit_loss = sell_value - (shares * buy_price)
        risk_control.update_account(profit_loss)
    
    return risk_control.current_capital

def optimize_parameters_adjusted(prices, initial_capital=1000000):
    """
    グリッドサーチにより、エントリーとエグジットの最適閾値を探索します。
    シミュレーションはリスク管理（RiskControl）の条件下で実行され、最終資産額を評価指標とします。
    
    パラメータ:
      prices         : 市場データ（NumPy配列）。
      initial_capital: 初期資本金。
      
    戻り値:
      best_params : (entry_threshold, exit_threshold) の最適パラメータ組。
      best_profit : その組み合わせでの最終資本金。
    """
    best_profit = -np.inf
    best_params = None

    # エントリーとエグジットの閾値候補（例：1%～5%の範囲を5分割）
    entry_candidates = np.linspace(0.01, 0.05, 5)
    exit_candidates  = np.linspace(0.01, 0.05, 5)
    
    for entry_threshold in entry_candidates:
        for exit_threshold in exit_candidates:
            profit = simulate_strategy_adjusted(prices, entry_threshold, exit_threshold, initial_capital)
            if profit > best_profit:
                best_profit = profit
                best_params = (entry_threshold, exit_threshold)
                print(f"新しい最適パラメータ発見: entry_threshold={entry_threshold:.3f}, exit_threshold={exit_threshold:.3f}, Profit={profit:.2f}")
    
    return best_params, best_profit

if __name__ == "__main__":
    # 市場データの取得（CSVファイル 'market_data.csv' から読み込み）
    prices = load_market_data('market_data.csv')
    if prices is None:
        # CSV読み込みに失敗した場合は、代替としてランダムウォークによるダミーデータを生成
        np.random.seed(42)
        days = 252  # 約1年分の営業日
        daily_returns = np.random.normal(0, 0.01, days)
        prices = 100 * np.cumprod(1 + daily_returns)
        print("ダミーの価格データを生成しました。")

    best_params, best_profit = optimize_parameters_adjusted(prices)
    
    print("最適なパラメータ (entry_threshold, exit_threshold):", best_params)
    print(f"シミュレーション結果（最終資産額）: {best_profit:,.0f} 円")
