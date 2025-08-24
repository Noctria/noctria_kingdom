# Security: Secrets Handling Policy
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / Security

---

## 0. 範囲
Do 層・DecisionEngine・Airflow・BrokerAdapter に関わる**機密情報**の取り扱い。

---

## 1. 秘匿対象
- `IDEMPO_SECRET`（idempotency_key 生成材料）
- DB 接続情報：`POSTGRES_USER/PASSWORD/DB/HOST`
- ブローカー資格情報：API Key / Client ID / Secret
- 署名鍵：HMAC/JWT 用

---

## 2. 保管方針
- **Secrets Manager / KMS** を一次保管  
- ランタイム渡しは **環境変数**（短命）  
- **Git にコミット禁止**（検知フック導入推奨）

---

## 3. 参照方法
- アプリ起動時に `ENV` を読み込み、**プロセス内キャッシュ**  
- ログ出力は **全てマスク**（先頭/末尾2〜4文字のみ）

---

## 4. ローテーション
- 重要キー（Broker/DB）：**90日**  
- `IDEMPO_SECRET`：**180日**（旧キーは 48h 併用）  
- 併用期間中は **key id** を付与して選択利用可能に

---

## 5. アクセス制御
- 最小権限（Do 層→ブローカー送信専用ロール）  
- 人間アクセスは break-glass のみ（監査記録必須）

---

## 6. インシデント対応
- 露出疑い検知 → **即失効** → ローテーション → 影響範囲調査  
- 影響判定に `idempo_ledger` / Outbox の監査ログを使用

---

## 7. 構成例（.env.sample）
```dotenv
# DB
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=airflow
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow

# Do layer
IDEMPO_SECRET=replace_me

# Broker
BROKER_API_KEY=replace_me
BROKER_API_SECRET=replace_me
```

---

## 8. 変更履歴
- **2025-08-24**: 初版
