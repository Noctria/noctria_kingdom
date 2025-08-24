# PDCA GUI — 画面仕様（ワイヤーフレーム & フィールド定義）
**Last Updated:** 2025-08-24 (JST)  
**Owner:** PDCA / Platform / UX

関連文書:
- `docs/apis/PDCA-GUI-API-Spec.md`
- `docs/apis/PDCA-Recheck-API-Spec.md`
- `docs/airflow/DAG-PDCA-Recheck.md`
- `docs/architecture/schema/PDCA-MetaSchema.md`

---

## 0. デザイン原則
- **運用優先**：状態の一目把握（健全/劣化/不明）と”再チェック”の即時操作
- **非同期志向**：APIは202返却、進捗はポーリング/プッシュで追跡
- **安全第一**：Idempotency、RateLimit、権限表示、破壊操作の確認ダイアログ
- **アクセシビリティ**：キーボード操作可、コントラスト AA、ARIA ロール
- **国際化**：i18n プレースホルダ（`t('…')`）で文言抽象化

---

## 1. 画面一覧
1. **S-01 戦略一覧**（Dashboard/List）
2. **S-02 戦略詳細**（Detail）
3. **S-03 再チェック実行ダイアログ**（Single/Bulk）
4. **S-04 リクエスト進捗**（Request Progress）
5. **S-05 成果物ビューア/ダウンロード**（Artifact Viewer）

---

## S-01 戦略一覧（Dashboard/List）
### ワイヤーフレーム
```
+----------------------------------------------------------------------------------+
| PDCA Dashboard                           [User: ops-ui]     [Create Recheck]     |
+----------------------------------------------------------------------------------+
| Search [ q: strat / title ]  Health [All|Healthy|Degraded|Unknown]  Tags [..]   |
| Instrument [USDJPY, EURUSD...]   Enabled [All|On|Off]   Sort [Last Check ▼]     |
|                                                                            [⟳] |
+----------------------------------------------------------------------------------+
| ID                    | Instrument | Health   | Last Checked        | Tags   | ⋯ |
| strat.meanrev.m1      | USDJPY     | ●Healthy | 2025-08-24 11:31    | daily  | 🔍|
| strat.breakout.h1     | USDJPY     | ▲Degrad. | 2025-08-24 10:50    | alert  | 🔍|
| strat.arb.l3          | EURUSD     | ?Unknown | —                   | exp    | 🔍|
+----------------------------------------------------------------------------------+
| Page 1 / 3    ◀ Prev   1  2  3  Next ▶                                          |
+----------------------------------------------------------------------------------+
Legend: ● Healthy  ▲ Degraded  ? Unknown
```

### データ・API
- GET `/gui/strategies?q=&tags_any=&health=&instrument=&enabled=&sort=&page=&page_size=`
- レスポンス: `items[].{id,title,instrument,enabled,last_health,last_checked_at,tags[]}`

### フィールド定義
| UI項目 | 型/制約 | 備考 |
|---|---|---|
| q | string(0..64) | ID/title の部分一致 |
| health | enum[] | `healthy,degraded,unknown` |
| tags_any | string[] | OR 条件 |
| instrument | string[] | OR 条件 |
| enabled | enum | `all,on,off` |
| sort | enum | `last_checked_at.desc`(既定), `id.asc` など |
| page,page_size | int | 1.. / 10..100 |

### 振る舞い
- 行末「🔍」で **S-02** へ遷移
- 「Create Recheck」で **S-03** をモーダル表示（単体/一括切替）
- オートリフレッシュ [⟳]：60s 間隔（トグルで停止可）

### 状態/エラー
- 空状態：”一致する戦略がありません”
- ローディング：テーブルスケルトン（3〜10 行）
- エラー：バナー（`t('load_failed')` 再試行ボタン）

---

## S-02 戦略詳細（Detail）
### ワイヤーフレーム
```
+----------------------------------------------------------------------------------+
| Strategy: strat.meanrev.m1        [Healthy ●]  [Recheck]  [Open Artifacts]      |
| Title: Mean Reversion M1                     Instrument: USDJPY  Enabled: On     |
+----------------------------------------------------------------------------------+
| KPI (30d):  Sharpe 1.10  | Winrate 0.56 | MaxDD 0.08   Last: 2025-08-24 11:31    |
| Chart(30d):  ────▁▂▃▅█▇▆▅▃▂─ …                                                 |
+----------------------------------------------------------------------------------+
| Recent Results (limit=20)                                                         |
| Completed At           | Health   | Sharpe | Winrate | MaxDD | RequestId  | ⋯    |
| 2025-08-24 11:31       | Healthy  | 1.25   | 0.57    | 0.07  | 01JABC…    | 🔗    |
| 2025-08-23 10:03       | Degraded | 0.70   | 0.49    | 0.12  | 01JDEF…    | 🔗    |
+----------------------------------------------------------------------------------+
```

### データ・API
- GET `/gui/strategies/:id?summary_window_days=30&limit_history=20`
- GET `/gui/strategies/:id/results?from=&to=&limit=`
- KPIグラフは results の時系列から描画

### フィールド定義
| セクション | キー | 型/制約 | 備考 |
|---|---|---|---|
| サマリ | kpi_avg | `{sharpe,winrate,max_dd}` | NaN/欠損は `null` |
| 履歴 | items[] | `completed_at,health,metrics{…},result_digest,request_id` | クリックで **S-04** |

### 操作
- [Recheck] → **S-03**（単体モードで `strategies=[id]` 固定）
- [Open Artifacts] → **S-05**（該当戦略の直近アーカイブ一覧）

---

## S-03 再チェック実行ダイアログ（Single/Bulk）
### ワイヤーフレーム
```
+-------------------------------- Recheck ----------------------------------------+
| Mode: (● Single / ○ Bulk)                                                       |
| Strategies: [ strat.meanrev.m1 ] [+Add]                                         |
| Window:  ( ) From [2025-08-10T00:00Z] To [2025-08-24T00:00Z]                    |
|          (●) Lookback [ 14 ] days                                               |
| Reason:  [ manual | daily-healthcheck | anomaly-detected | custom: ______ ]     |
| Params:  [x] recalc_metrics: (winrate)(sharpe)(max_dd)   [ ] retrain            |
| Dry Run: [x]                                                                     |
|                                                                 [Cancel] [Run]  |
+----------------------------------------------------------------------------------+
```

### 入出力・API
- 単体: `POST /pdca/recheck`（202 で `request_id`, `estimated`）
- 一括: `POST /pdca/recheck_all`
- Idempotency-Key: クライアントで ULID 生成（再送で同一キー）

### フィールド定義
| フィールド | 型/制約 | バリデーション |
|---|---|---|
| strategies[] | 1..50 | `/^[a-z0-9._-]+$/` |
| window.from/to or lookback_days | 相互排他 | 最大180日 |
| reason | enum or string(1..64) | 既定候補 + 任意 |
| params.recalc_metrics[] | enum | `winrate,sharpe,max_dd` |
| params.retrain | bool | 既定=false |
| dry_run | bool | 既定=true |

### UI ルール
- Dry Run 時：**Run** は「Estimate」と表示、結果件数（`estimated.strategies/batches`）をトースト表示
- 実行時：完了後 **S-04** に遷移（`request_id` を渡す）

---

## S-04 リクエスト進捗（Request Progress）
### ワイヤーフレーム
```
+------------------------------ Recheck Progress ---------------------------------+
| Request: 01JABCXYZ-ULID-5678      Status: Running ▷    [Refresh ⟳] [Back]       |
+----------------------------------------------------------------------------------+
| Batches: [■■□□□□]  1/5   Strategies: 12/60  Elapsed: 03:11                      |
| Failures: 2   Healthy: 9   Degraded: 3   Unknown: 0                              |
+----------------------------------------------------------------------------------+
| Recent Activity                                                                  |
| 11:31  strat.meanrev.m1   ✔ success  sharpe 1.25  report: …/artifacts/123        |
| 11:28  strat.breakout.h1  ✖ failed   reason=DATA_SOURCE_DOWN                     |
+----------------------------------------------------------------------------------+
| Report: [Download HTML] [Open Dashboard]                                         |
+----------------------------------------------------------------------------------+
```

### データ・API
- GET `/gui/requests/:request_id`
- ポーリング：5s（手動更新ボタン [⟳] も提供）

### 表示項目
- `status`（`running|success|failed`）
- 進捗: `total_batches/completed_batches`, `total_strategies/completed_strategies`
- サマリ: 成功/失敗/健康分布
- 最新アクティビティ（ログ風）— 直近 20 件

---

## S-05 成果物ビューア/ダウンロード（Artifact Viewer）
### ワイヤーフレーム
```
+------------------------------ Artifacts ----------------------------------------+
| Strategy: strat.meanrev.m1           [Back]                                     |
+----------------------------------------------------------------------------------+
| Filter: Kind [All|chart|report|csv]   Range: [ from ][ to ]   [Search q] [⟳]    |
+----------------------------------------------------------------------------------+
| ID   | Kind   | Created At           | Size   | Action                           |
| 123  | chart  | 2025-08-24 11:31     | 120KB  | [Preview] [Download]             |
| 777  | report | 2025-08-24 03:54     | 890KB  | [Open] [Download]                |
+----------------------------------------------------------------------------------+
```

### データ・API
- GET `/gui/strategies/:id`（artifacts 概要）
- GET `/gui/artifacts/:artifact_id/url` → 短命の署名付き URL
- 画像系はモーダルでプレビュー、レポートは新規タブ

### フィールド
| 項目 | 型 | 備考 |
|---|---|---|
| kind | enum | `chart,report,csv,other` |
| url | string | 期限付き、ダウンロード時のみ生成 |
| bytes_size | number | ヒト可読表示（KB/MB） |

---

## 2. 共通UIコンポーネント仕様
### ステータスバッジ
- Healthy: 緑 ●, aria-label=`t('healthy')`
- Degraded: 黄 ▲, aria-label=`t('degraded')`
- Unknown: 灰 ?, aria-label=`t('unknown')`

### 日付/時刻表示
- 既定: ローカルタイムゾーン（JST） + ISO 表示
- ツールチップに UTC を併記

### テーブル
- 列並べ替え：`Last Checked`/`ID`/`Instrument`/`Health`
- ページング：ページ番号 + 総件数
- 空/エラー/ロード時の3状態を統一スタイルで提供

---

## 3. アクセシビリティ
- キーボードタブ順の設計、モーダルはフォーカストラップ
- 重要ボタン（Run/Download）は `aria-disabled` とショートカット（例: Alt+R）
- グラフには**数値テーブル代替**を必ず表示

---

## 4. セキュリティ/権限表示
- ユーザの `scopes` をヘッダに表示（例: `pdca:read, pdca:recheck`）
- 権限不足時は**非表示**もしくは**disabled**＋ツールチップ（”権限が必要です”）
- 署名付きURLは**都度発行**（コピーガードの注意文を表示）

---

## 5. エラーハンドリング（HTTP → UI）
| HTTP | 表示 | 再試行 |
|---|---|---|
| 400/422 | 入力エラー行にインライン表示 | 修正後送信 |
| 401/403 | トースト + ログイン導線 | 再ログイン |
| 409 | ダイアログ（Idempotency 差分） | 送信内容を確認 |
| 429 | トースト（Retry-After 秒） | 自動再試行抑制 |
| 5xx/502 | バナー（Airflow/Server） | リトライボタン |

---

## 6. イベント追跡/テレメトリ
- `ui.action`：`recheck.run`, `recheck.dryrun`, `artifact.download`, `list.filter`
- `ui.latency_ms`：API往復時間（エンドポイント別）
- `ui.error_total{code}`：HTTP エラー種別

---

## 7. 設定（フロントエンド .env）
| KEY | 既定 | 説明 |
|---|---|---|
| `VITE_API_BASE` | `http://localhost:8001` | API ベースURL |
| `VITE_POLL_INTERVAL_MS` | `5000` | 進捗ポーリング |
| `VITE_PAGE_SIZE_DEFAULT` | `50` | 一覧の件数 |
| `VITE_SIGNED_URL_TTL` | `300` | ダウンロード URL の寿命（秒） |

---

## 8. i18n キー例
```
dashboard.title = "PDCA Dashboard"
status.healthy = "Healthy"
status.degraded = "Degraded"
status.unknown = "Unknown"
action.recheck = "Recheck"
action.refresh = "Refresh"
msg.no_data = "No items found"
msg.load_failed = "Failed to load"
```

---

## 9. 変更履歴
- **2025-08-24**: 初版（一覧/詳細/再チェック/進捗/成果物、共通UI、A11y、i18n）
