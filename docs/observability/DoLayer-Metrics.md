# Observability: Do-Layer Metrics
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Do-Layer / SRE

---

## 0. 目的
Do 層の注文処理に関する**信頼性・性能・幂等挙動**を可視化し、SLO 監視／障害対応を可能にする。

---

## 1. メトリクス一覧（Prometheus想定）
### 1.1 主要カウンタ
- `order_requests_total{outcome}`  
  - `outcome ∈ {accepted,succeeded,failed,conflict,validation,rate_limited}`  
  - 受け入れ→確定の**全流量**を把握。
- `idempotency_conflicts_total`  
  - 409 発生回数。**上昇=クライアント不具合**の兆候。
- `broker_requests_total{adapter,outcome}`  
  - 送信結果: `ok|timeout|down|rejected|internal`

### 1.2 レイテンシ（ヒストグラム）
- `do_order_latency_ms{phase}`  
  - `phase ∈ {validation,broker_rtt,total}`  
  - SLA: P95 `total` ≤ 300ms（IOCの目安）

### 1.3 ゲージ／サマリ
- `outbox_pending_count`（P1導入後）  
- `idempo_ledger_rows`（TTL 清掃の健全性）

---

## 2. SLO / SLI
- 可用性 SLO（30日ローリング）
  - `success = order_requests_total{outcome="succeeded"}`
  - `total = sum(order_requests_total{outcome=~"accepted|succeeded|failed"})`
  - `availability = success / total >= 99.5%`
- レイテンシ SLO
  - `P95(do_order_latency_ms{phase="total"}) <= 300ms`

---

## 3. アラート（Alertmanager 例）
- `availability < 99% for 30m` → **page**  
- `idempotency_conflicts_total` の 1h 増分 > 50 → **ticket**  
- `broker_requests_total{outcome="timeout"}` 5m で > 20 → **page**  
- `outbox_pending_count > 1000` かつ 15m 連続 → **page**

---

## 4. ログ & トレース
- **構造化ログ（JSON）**
  - keys: `trace_id, idempotency_key, request_digest, result_digest, status, reason_code, latency_ms.total`
- **Tracing**
  - root span: `do.order`（attributes: idem_key hash化、instrument）  
  - child span: `broker.send`（adapter 名、rtt）

---

## 5. ダッシュボード（概要）
- パネル1: 成功率（stacked outcome）  
- パネル2: レイテンシ（P50/P95）  
- パネル3: 409 件数の時系列 & 直近クライアントTOP  
- パネル4: ブローカー別 成功/失敗、タイムアウト率  
- パネル5: Outbox pending（P1以降）

---

## 6. 変更履歴
- **2025-08-24**: 初版
