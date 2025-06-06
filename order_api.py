from flask import Flask, request, jsonify
import MetaTrader5 as mt5

app = Flask(__name__)

@app.route("/order", methods=["POST"])
def execute_order():
    data = request.json
    symbol = data.get("symbol")
    lot = data.get("lot")
    order_type = data.get("type")  # "buy" or "sell"

    if not mt5.initialize():
        return jsonify({"status": "error", "message": "MT5初期化失敗"})

    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL,
        "price": mt5.symbol_info_tick(symbol).ask,
        "deviation": 20,
        "magic": 123456,
        "comment": "Noctria trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    result = mt5.order_send(order_request)
    mt5.shutdown()
    return jsonify({"status": "ok", "result": str(result)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
