# optimized_order_execution.py
import time
import random

class OrderExecution:
    """
    注文執行ロジックの最適化を行うクラス（Fintokei用）
    
    このクラスは、注文実行における以下の課題に対応します：
      - スリッページの削減
      - 分割注文による部分約定
      - リトライ機構による失注防止
    """
    
    def __init__(self, max_retry=3, retry_delay=0.1, slippage_threshold=0.001):
        """
        Parameters:
          max_retry: 注文再実行の最大回数
          retry_delay: 再実行間の待機時間（秒）
          slippage_threshold: 許容スリッページ（例: 0.001 は 0.1%）
        """
        self.max_retry = max_retry
        self.retry_delay = retry_delay
        self.slippage_threshold = slippage_threshold

    def execute_order(self, order_type, quantity, target_price, market_price):
        """
        注文を送信し、適切な注文執行をシミュレーションします。
        ※本来は取引APIとの連携により実際のオーダーが実行されるコードですが、
        ここではシミュレーションとしての動作例を示します。
        
        Parameters:
          order_type: 'buy' または 'sell'
          quantity: 注文数量（ロット数）
          target_price: 希望注文価格
          market_price: 注文送信時の現在の市場価格

        Returns:
          executed_quantity: 命令が実行された総数量
          average_price: 実際の平均約定価格
        """
        # 注文実行前に許容スリッページのチェック
        expected_slippage = abs(market_price - target_price) / target_price
        if expected_slippage > self.slippage_threshold:
            print(f"【警告】許容スリッページを超えています（{expected_slippage*100:.2f}%）。注文キャンセルまたは価格再設定を検討してください。")
            return 0, None

        executed_quantity = 0
        total_cost = 0
        attempt = 0
        remaining_qty = quantity

        # 分割注文の実行ロジック
        while remaining_qty > 0 and attempt < self.max_retry:
            attempt += 1
            # 約定数量をランダムに決定（50%～100% の割合で約定と仮定）
            executed = remaining_qty * random.uniform(0.5, 1.0)
            executed = max(1, int(executed))  # 最低でも 1 単位は執行
            # 実際の価格は市場価格に僅かなばらつきを加味
            actual_price = market_price * random.uniform(0.999, 1.001)
            cost = executed * actual_price

            executed_quantity += executed
            total_cost += cost
            remaining_qty -= executed

            print(f"[Attempt {attempt}] 約定数量: {executed}, 残数量: {remaining_qty}")

            # 待機時間をおいて再実行
            time.sleep(self.retry_delay)

            # シミュレーションのため市場価格も更新（本番では最新の市場データを取得）
            market_price *= random.uniform(0.999, 1.001)

        if executed_quantity == 0:
            print("注文執行が完全に失敗しました。")
            return 0, None

        average_price = total_cost / executed_quantity
        print(f"総約定数量: {executed_quantity}, 平均取引価格: {average_price:.4f}")
        return executed_quantity, average_price

# シンプルなテストシミュレーション
if __name__ == "__main__":
    executor = OrderExecution(max_retry=3, retry_delay=0.1, slippage_threshold=0.001)
    order_type = "buy"
    quantity = 100         # 注文数量
    target_price = 100.0   # ターゲット注文価格
    market_price = 100.0   # 現在の市場価格（初期値）

    executed_qty, avg_price = executor.execute_order(order_type, quantity, target_price, market_price)
    print(f"注文結果：実行数量 = {executed_qty}, 平均約定価格 = {avg_price}")
