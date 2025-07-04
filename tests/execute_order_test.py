from core.path_config import *
import sys
import os

from order_execution import OrderExecution  # execution/order_execution.py

if __name__ == "__main__":
    executor = OrderExecution(api_url="http://192.168.11.30:5001/order")
    result = executor.execute_order("USDJPY", 0.1, order_type="buy")
    print("MT5注文結果:", result)
