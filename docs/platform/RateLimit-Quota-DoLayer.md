# Do-Layer: Rate Limit / Quota 設計
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / SRE

---

## 0. 目的
ブローカー安全運用と安定SLOのため、Do 層の入口で **Rate Limit** と **日次クォータ**を設ける。

---

## 1. 単位・キー
- **キー:** `client_id (JWT.sub)` + `instrument`（将来オプション）  
- **ウィンドウ:** 1分窓（固定）+ スライディング

---

## 2. 既定値（初期）
- **Rate:** `60 req/min/client`  
- **Burst:** `30`（トークンバケット）  
- **Daily Quota:** `10,000 req/day/client`（超過は 429）

> ブローカー制限を鑑み、将来 `instrument` 追加で細分化可能。

---

## 3. 応答
- 429 Too Many Requests  
  - ヘッダ:  
    - `X-RateLimit-Limit: 60`  
    - `X-RateLimit-Remaining: <n>`  
    - `Retry-After: <seconds>`
  - ボディ: `{"error":"RATE_LIMITED","retry_after":...}`

---

## 4. 実装メモ
- in-memory（uvicorn） or Redis ベース  
- Key: `rl:<client_id>:<yyyy-mm-ddThh:mm>`  
- 失敗系もカウント（DoS 回避）。429 は観測対象。

---

## 5. 監視
- `rate_limited_total{client_id}`  
- `quota_exceeded_total{client_id}`  
- ダッシュボードで**頻出クライアント**を可視化

---

## 6. 運用
- 例外許可（ホワイトリスト）は **一時的**（期限付き）  
- 値変更は Feature Flag/環境変数で即時反映

---

## 7. 変更履歴
- **2025-08-24**: 初版
