double CalculateScalpingSignal()
{
    double price_changes[] = {0.002, -0.001, 0.003, -0.002, 0.004};
    return ArrayAverage(price_changes);
}

void ExecuteScalpingTrade()
{
    double scalping_signal = CalculateScalpingSignal();
    
    if(scalping_signal > 0.002)
    {
        ExecuteTrade(ORDER_TYPE_BUY, 0.05);
    }
    else if(scalping_signal < -0.002)
    {
        ExecuteTrade(ORDER_TYPE_SELL, 0.05);
    }
}
