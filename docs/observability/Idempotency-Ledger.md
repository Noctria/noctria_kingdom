\# Observability: Idempotency Ledger (Draft v0.1)

\*\*Last Updated:\*\* 2025-08-24 (JST)  

\*\*Purpose:\*\* 変更系 API の幂等性を保証し、結果の再提示と競合検出を高速化するための台帳。



---



\## 0. 概要

\- Do-Layer の注文実行 API (`/do/order`) で利用される `Idempotency-Key` の結果を記録。  

\- 同じキーの再送に対しては過去の結果を即座に返し、差分がある場合は `409 Conflict` を返す。  

\- 競合発生はメトリクス化し、GUI HUD の \*\*「API健全性カード」\*\* に反映。



---



\## 1. テーブル設計（RDB 案）

```sql

CREATE TABLE IF NOT EXISTS idempo\_ledger (

&nbsp; idempotency\_key       TEXT PRIMARY KEY,

&nbsp; request\_digest        TEXT NOT NULL,

&nbsp; result\_digest         TEXT,

&nbsp; status                TEXT NOT NULL CHECK (status IN ('accepted','succeeded','failed')),

&nbsp; first\_seen\_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

&nbsp; last\_seen\_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

&nbsp; expires\_at            TIMESTAMPTZ NOT NULL,

&nbsp; response\_payload\_json JSONB,

&nbsp; http\_status           INT NOT NULL,

&nbsp; UNIQUE (idempotency\_key)

);



CREATE INDEX IF NOT EXISTS idx\_idempo\_ledger\_expires

&nbsp; ON idempo\_ledger (expires\_at);

```



---



\## 1.1 ダイジェスト

\- `request\_digest`: ボディの正規化 JSON を SHA256 ハッシュ化  

\- `result\_digest`: 正常応答の主要フィールドから SHA256 ハッシュ生成  



---



\## 2. 動作フロー

1\. 受信時に `Idempotency-Key` を検索  

2\. 未登録なら `accepted` として仮登録（`request\_digest` 記録）  

3\. 実行成功時に `succeeded` に更新（結果を保存）  

4\. 同一キー再送時  

&nbsp;  - `request\_digest` が完全一致 → `200 OK` と前回結果を返す  

&nbsp;  - 差分あり → `409 Conflict`  



---



\## 3. 運用

\- `expires\_at`: 24〜72h を推奨（ブローカー SLA と整合）  

\- TTL 経過したエントリは定期ジョブで削除  

\- 高速用途では KV ストア（Redis/Memcached）＋RDB バックフィルのハイブリッド運用も可  



---



\## 4. 可観測性・監査

\- `status` の分布をメトリクスに集計（accepted / succeeded / failed / conflict）  

\- 競合（409）が発生した場合はアラートを挙げ、GUI HUD に可視化  

\- `response\_payload\_json` に保存された応答はデバッグ・再現性確保に利用可能  



