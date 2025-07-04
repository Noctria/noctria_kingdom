import json
from flask import Flask, request
import pandas as pd

app = Flask(__name__)

def process_tradingview_data(data):
    """TradingViewから受信したデータを処理"""
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df

@app.route("/webhook", methods=["POST"])
def webhook():
    """TradingView Webhookのデータを受信"""
    content = request.json
    parsed_data = process_tradingview_data(content)
    
    print("Received TradingView Data:", parsed_data)
    
    return {"status": "success"}

if __name__ == "__main__":
    app.run(port=5000, debug=True)
