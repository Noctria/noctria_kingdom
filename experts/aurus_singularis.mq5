double GetMarketSentiment()
{
    double rsi = iRSI(NULL, 0, 14, PRICE_CLOSE, 0);
    double macd = iMACD(NULL, 0, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
    double atr = iATR(NULL, 0, 14, 0);
    
    return (rsi - 50) / 100 + macd / 100 + atr / 200;
}

double EvaluateRisk()
{
    double spread = MarketInfo(Symbol(), MODE_SPREAD);
    double volatility = iATR(NULL, 0, 14, 0);
    
    return spread + volatility;
}

void ExecuteTrade(int orderType, double lot)
{
    MqlTradeRequest request;
    request.action = TRADE_ACTION_DEAL;
    request.type = (orderType == ORDER_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.volume = lot;
    request.price = SymbolInfoDouble(Symbol(), SYMBOL_BID);
    
    OrderSend(request);
}
