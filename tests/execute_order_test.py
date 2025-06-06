# execute_order_test.py
from order_execution import OrderExecution  # 事前にorder_execution.pyにまとめた場合
# またはクラス部分を直接ここにペーストしてもOK

if __name__ == "__main__":
    executor = OrderExecution(api_url="http://192.168.11.30:5001/order")
    result = executor.execute_order("USDJPY", 0.1, order_type="buy")
    print("MT5注文結果:", result)
