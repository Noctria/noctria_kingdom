#include "aurus_singularis.mq5"
#include "levia_tempest.mq5"
#include "noctus_sentinella.mq5"
#include "prometheus_oracle.mq5"

input int magic_number = 999999;
input double lot_size = 0.1;
input double risk_tolerance = 2.0;

void OnTick()
{
    double market_sentiment = GetMarketSentiment();
    double risk_level = EvaluateRisk();

    if(market_sentiment > 0.5 && risk_level < risk_tolerance)
    {
        ExecuteTrade(ORDER_TYPE_BUY, lot_size);
    }
    else if(market_sentiment < -0.5 && risk_level < risk_tolerance)
    {
        ExecuteTrade(ORDER_TYPE_SELL, lot_size);
    }
}
