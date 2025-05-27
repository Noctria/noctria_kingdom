import pandas as pd
import numpy as np

class SentimentAnalysis:
    """市場心理を分析し、投資判断に活用するモジュール"""
    
    def __init__(self):
        self.sentiment_threshold = 0.5  # 強気・弱気の閾値
    
    def analyze_sentiment(self, news_data):
        """市場ニュースデータからセンチメントを抽出"""
        sentiment_scores = np.random.uniform(-1, 1, len(news_data))  # 仮のスコア適用
        return pd.DataFrame({"news": news_data, "sentiment": sentiment_scores})

    def classify_market_mood(self, sentiment_scores):
        """センチメントの平均値で市場の方向性を分類"""
        avg_sentiment = np.mean(sentiment_scores)
        if avg_sentiment > self.sentiment_threshold:
            return "BULLISH"
        elif avg_sentiment < -self.sentiment_threshold:
            return "BEARISH"
        else:
            return "NEUTRAL"

# ✅ 市場心理解析テスト
if __name__ == "__main__":
    sample_news = ["米国の雇用統計が予想を上回る", "中央銀行が金利引き上げを発表", "地政学リスクの高まりが懸念"]
    analyzer = SentimentAnalysis()
    
    sentiment_results = analyzer.analyze_sentiment(sample_news)
    market_mood = analyzer.classify_market_mood(sentiment_results["sentiment"])

    print("Sentiment Analysis Results:\n", sentiment_results)
    print("Market Mood Classification:", market_mood)
