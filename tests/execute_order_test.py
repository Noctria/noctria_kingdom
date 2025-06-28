import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'execution')))

from order_execution import OrderExecution  # execution/order_execution.py

if __name__ == "__main__":
    executor = OrderExecution(api_url="http://192.168.11.30:5001/order")
    result = executor.execute_order("USDJPY", 0.1, order_type="buy")
    print("MT5注文結果:", result)
