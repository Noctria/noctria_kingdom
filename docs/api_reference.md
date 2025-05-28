# Noctria Kingdom - API 仕様書

## 概要
Noctria Kingdom では、外部アプリケーションやサービスとの連携を可能にする API を提供します。  
本 API を利用することで、戦略適用、データ取得、注文実行などの機能を外部システムから操作できます。

---

## 📂 API一覧

| API 名 | メソッド | 説明 | エンドポイント |
|--------|--------|------|--------------|
| `GetMarketData` | `GET` | 市場データを取得 | `/api/market/data` |
| `GetTradeSignal` | `GET` | 現在のトレードシグナルを取得 | `/api/trade/signal` |
| `ExecuteTrade` | `POST` | トレード注文を実行 | `/api/trade/execute` |
| `GetRiskAssessment` | `GET` | リスク管理の評価 | `/api/risk/assessment` |
| `OptimizeStrategy` | `POST` | 戦略最適化を適用 | `/api/strategy/optimize` |
| `BacktestStrategy` | `POST` | バックテストを実行 | `/api/test/backtest` |

---

## 🏦 **市場データ取得**
### `GET /api/market/data`
**説明:**  
市場の価格データやボラティリティ情報を取得します。

**レスポンス例:**
```json
{
  "symbol": "EURUSD",
  "price": 1.2543,
  "spread": 0.0002,
  "volatility": 0.015
}
