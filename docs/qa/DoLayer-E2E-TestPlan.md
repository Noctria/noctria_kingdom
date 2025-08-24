# QA: Do-Layer E2E Test Plan
**Last Updated:** 2025-08-24 (JST)  
**Owner:** QA / Do-Layer

---

## 0. 目的
`/do/order` の**幂等性/信頼性/性能**を E2E で検証し、回帰防止のスイートを確立。

---

## 1. 前提
- `idempo_ledger` テーブル作成済み  
- PaperAdapter 有効（実ブローカーはモックでも可）  
- `IDEMPO_SECRET`/DB接続 は .env 経由

---

## 2. テスト項目
### 2.1 幂等（同一キー）
- **T-101**: 初回 → 201、再送（完全一致）→ 200 同レスポンス  
- **T-102**: 同一キーでボディ差分 → 409

### 2.2 バリデーション
- **T-201**: ヘッダ/ボディ不一致 → 422  
- **T-202**: qty 下限未満 → 422  
- **T-203**: instrument 非許可 → 422

### 2.3 ブローカー例外
- **T-301**: タイムアウト → 502/504（理由コード `BROKER_TIMEOUT`）  
- **T-302**: ダウン → 503（`BROKER_DOWN`）  
- **T-303**: 業務拒否 → 400/409（`BROKER_REJECTED`）

### 2.4 回復性
- **T-401**: 201 の後にクライアント再送 → 200（過去結果）  
- **T-402**: アプリ再起動後も 200 を返却（台帳維持）

### 2.5 性能
- **T-501**: 単発 P95 `total` < 300ms  
- **T-502**: 60RPM で 5分 → エラー率 < 1%

### 2.6 Outbox（P1以降）
- **T-601**: pending→sending→succeeded の遷移  
- **T-602**: 送信失敗時の backoff 再送で成功に至る  
- **T-603**: 最大試行超過で aborted

---

## 3. 手順テンプレ（curl）
```bash
# 初回
KEY=01JTESTULIDXYZ
BODY='{"order_id":"tc-1","instrument":"USDJPY","side":"BUY","qty":0.1,"price":null,"time_in_force":"IOC","tags":["qa"],"idempotency_key":"'$KEY'","requested_at":"2025-08-24T00:00:00Z","risk_constraints":{"max_dd":0.1,"max_consecutive_loss":3,"max_spread":0.002}}'
curl -sS -X POST http://localhost:8000/do/order -H "Content-Type: application/json" -H "Idempotency-Key: $KEY" -d "$BODY"

# 再送（完全一致）
curl -sS -X POST http://localhost:8000/do/order -H "Content-Type: application/json" -H "Idempotency-Key: $KEY" -d "$BODY"
```

---

## 4. 成功判定
- 期待 HTTP / レスポンス本文が一致  
- `idempo_ledger` の `status`・`result_digest` が整合  
- メトリクスが閾値内（SLOを満たす）

---

## 5. レポート
- 各ケースの **Given/When/Then** を記載  
- 重要なケースは **再現手順** と **実ログ** を貼付

---

## 6. 変更履歴
- **2025-08-24**: 初版
