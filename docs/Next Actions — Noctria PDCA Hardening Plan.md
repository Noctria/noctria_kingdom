<!-- AUTODOC:BEGIN mode=file_content path_globs="/mnt/d/noctria_kingdom/docs/_partials_full/docs/Next Actions — Noctria PDCA Hardening Plan.md" -->
# ✅ Next Actions — Noctria PDCA Hardening Plan

## M1. DO層の堅牢化（今日から）
- [ ] **Noctus Gate（最小実装）**：`src/execution/risk_gate.py`
  - [ ] ルール: position上限 / 1トレースあたりのmax notional / 連敗時のqty縮小 / 取引時間帯制限
  - [ ] 入力: `order_request.json` + `risk_policy.json` + `trace_id`
  - [ ] 出力: 許可された `order_request`（必要なら qty clamp / FLAT 化）
  - [ ] 監査: ブロック/縮小理由を `obs_alerts` に記録（severity, policy_name, trace_id）
  - [ ] **受け入れ基準**: デモ1本で `obs_alerts` が0～1件生成、`obs_exec_events` と `obs_decisions` の trace_id が一致
- [ ] **Idempotency** 一気通貫
  - [ ] `OrderRequest` に `idempotency_key` を追加（`symbol|side|qty|ts_floor_minute|trace_id` を HMAC-SHA256）
  - [ ] `generate_order_json.py` で署名付け：`hmac_sha256(payload, SECRET)`
  - [ ] **Outbox** テーブル（ユニーク: `idempotency_key`）＋リトライ（一意制約違反でスキップ）
  - [ ] `exec_result` に `idempotency_key` を必ず含める
  - [ ] **受け入れ基準**: 同一リクエストを2回投げても **BROKER送信は1回**、`obs_exec_events` は重複しない
- [ ] **QualityGate 仕上げ**（P→D手前）
  - [ ] `missing_ratio`/`data_lag` で `OK/SCALE/FLAT` を安定判定
  - [ ] `SCALE` の倍率と理由を `obs_decisions.reason` に出力
- [ ] **観測スキーマの穴埋め**
  - [ ] `obs_alerts`（trace_id, policy, reason, severity, created_at）
  - [ ] `obs_do_metrics`（trace_id, child_orders, retry_counts など；将来用）
  - [ ] ビュー: `obs_trace_timeline`, `obs_trace_latency`（既存OK）、**アラートもタイムラインに載るよう拡張**

### 提案サンプル（YAML・SQL・Pythonの雛形）

**`configs/risk_policy.yml`**
```yaml
default:
  max_position_notional: 100000        # JPY
  max_order_qty: 20000                 # units
  trading_hours_utc: ["00:00-22:00"]   # 例
  max_consecutive_losses: 3
  shrink_after_losses_pct: 50          # 次回qtyを50%縮小
  forbidden_symbols: []
overrides:
  USDJPY:
    max_position_notional: 150000
```

**Outbox DDL（PostgreSQL）**
```sql
CREATE TABLE IF NOT EXISTS outbox_orders (
  id BIGSERIAL PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  trace_id TEXT,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ,
  broker_response JSONB
);
```

**Idempotency Key 生成（Python片）**
```python
import hmac, hashlib, json, os
SECRET = os.getenv("NOCTRIA_IDEMPOTENCY_SECRET", "dev-secret")
def make_idem_key(symbol, side, qty, trace_id, ts_floor_min):
    base = f"{symbol}|{side}|{round(float(qty), 6)}|{ts_floor_min}|{trace_id}"
    return hmac.new(SECRET.encode(), base.encode(), hashlib.sha256).hexdigest()[:32]
```

---

## M2. Decision/Config の拡張（今週）
- [ ] `profiles.yaml` で **weights / rollout_percent / combine / min_confidence / alpha_risk** を管理
- [ ] RoyalDecisionEngine を **`weighted_sum`** までE2E実証（方向一致合算）
- [ ] `obs_decisions.features.top_candidates` を **上位5件**まで記録（今は3件）
- [ ] A/B ロールアウト（7%→30%→100%）の **スイッチをGUIに露出**（read-onlyでもOK）

**`configs/profiles.yaml` の例**
```yaml
default:
  rollout_percent: 30
  min_confidence: 0.4
  combine: weighted_sum
  alpha_risk: 0.35
weights:
  Aurus: 0.8
  Levia: 0.7
  Prometheus: 0.9
  Veritas: 1.0
```

---

## M3. 運用の自動化（来週以降）
- [ ] **Airflow DAG**：`pdca_minidemo_dag.py`
  - [ ] PLAN→AI→DECISION→DO の最小チェーンを **1h** 間隔で実行
  - [ ] `X-Trace-Id` をタスク間で XCom 伝搬
  - [ ] 失敗時リトライ＋冪等設計確認（Outbox が効くこと）
- [ ] **アラート閾値**：`obs_slo_violations_24h` をベースに Slack/Webhook 通知
- [ ] **日次マテビュー更新**：`obs_latency_daily` を cron で自動 `REFRESH CONCURRENTLY`

---

## 参考：受け入れテスト（psql一発）
- [ ] タイムライン整合
  ```sql
  SELECT ts,kind,action FROM obs_trace_timeline WHERE trace_id='{TID}' ORDER BY ts;
  ```
- [ ] レイテンシ分解
  ```sql
  SELECT * FROM obs_trace_latency WHERE trace_id='{TID}';
  ```
- [ ] 重複送信防止（idempotency）
  ```sql
  SELECT idempotency_key, COUNT(*) FROM outbox_orders GROUP BY 1 HAVING COUNT(*)>1;
  -- → 0 行が合格
  ```

---

## さらに先（バックログ）
- [ ] DO層FSM（place→ack→partial_fill→filled/expired/rejected）
- [ ] Broker Capabilities ハンドシェイク（min_qty, step, tif, replace可否）
- [ ] CHECK層の **P95 KPI** ダッシュボード（Grafana/Metabase）
- [ ] ACT層の自動昇格/ロールバック（Two-Person + King 承認フロー付き）
- [ ] モデルレジストリの署名/指紋/評価リンク（SoT強化）
<!-- AUTODOC:END -->
