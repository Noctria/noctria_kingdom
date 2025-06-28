#include "aurus_singularis.mq5"
#include "levia_tempest.mq5"
#include "noctus_sentinella.mq5"
#include "prometheus_oracle.mq5"

input int magic_number = 999999;
input double lot_size = 0.1;
input double risk_tolerance = 2.0;

void CheckTradeSignal()
{
    string filename = "trade_signal.csv";
    int handle = FileOpen(filename, FILE_READ | FILE_CSV);
    
    if (handle < 0) return;  // ファイルが開けない場合は処理終了

    string symbol;
    int orderType;
    double lotSize;

    // CSVからデータを読み取る
    if (FileReadString(handle, symbol) && FileReadInteger(handle, orderType) && FileReadDouble(handle, lotSize))
    {
        ExecuteTrade(orderType, lotSize);  // Pythonからの注文を実行
        Print("✅ Trade executed from Python signal: ", orderType, ", Lot:", lotSize);
    }
    
    FileClose(handle);
}

void OnTick()
{
    double market_sentiment = GetMarketSentiment();
    double risk_level = EvaluateRisk();
    double spread = MarketInfo(Symbol(), MODE_SPREAD);
    double trend = iMA(NULL, 0, 14, 0, MODE_SMA, PRICE_CLOSE, 0);
    double volatility = iATR(NULL, 0, 14, 0);

    // スプレッドが広すぎる場合は取引を回避
    if (spread > 5) 
    {
        Print("❌ スプレッド拡大 → 取引回避");
        return;
    }

    // 市場センチメント & トレンド & ボラティリティを考慮し、売買決定
    if (market_sentiment > 0.5 && risk_level < risk_tolerance && trend > 0 && volatility < 1.5)
    {
        ExecuteTrade(ORDER_TYPE_BUY, lot_size);
        Print("✅ BUY注文実行 - Sentiment:", market_sentiment, ", Risk:", risk_level);
    }
    else if (market_sentiment < -0.5 && risk_level < risk_tolerance && trend < 0 && volatility < 1.5)
    {
        ExecuteTrade(ORDER_TYPE_SELL, lot_size);
        Print("✅ SELL注文実行 - Sentiment:", market_sentiment, ", Risk:", risk_level);
    }
    else
    {
        Print("⚠️ 市場不安定 → HOLD");
    }

    // Python注文シグナルをチェック
    CheckTradeSignal();
}
