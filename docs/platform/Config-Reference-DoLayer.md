# Do-Layer: Configuration Reference
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform

---

## 0. 目的
Do 層サービスの起動に必要な **環境変数**と既定値を一覧化する。

---

## 1. サービス基本
| 変数 | 既定 | 説明 |
|---|---|---|
| `DO_PORT` | `8000` | HTTP ポート |
| `DO_LOG_LEVEL` | `info` | `debug/info/warn/error` |
| `DO_ENV` | `dev` | `dev/stg/prod` |
| `DO_FEATURE_OUTBOX` | `false` | P1 導入フラグ |

---

## 2. データベース
| 変数 | 既定 | 説明 |
|---|---|---|
| `POSTGRES_HOST` | `postgres` | ホスト名 |
| `POSTGRES_PORT` | `5432` | ポート |
| `POSTGRES_DB` | `airflow` | DB名 |
| `POSTGRES_USER` | `airflow` | ユーザー |
| `POSTGRES_PASSWORD` | なし | パスワード |

---

## 3. 認証/認可
| 変数 | 既定 | 説明 |
|---|---|---|
| `DO_JWT_AUDIENCE` | `do-layer` | 受信者 |
| `DO_JWT_ISSUER` | `noctria.auth` | 発行者 |
| `DO_JWKS_URL` | なし | JWKS のURL |
| `DO_JWT_PUBLIC_KEY_BASE64` | なし | 直接鍵を渡す場合 |

---

## 4. 幂等/TTL
| 変数 | 既定 | 説明 |
|---|---|---|
| `IDEMPO_TTL_HOURS` | `48` | idempo_ledger の TTL |
| `IDEMPO_SECRET` | なし | キー生成/検証用 |

---

## 5. Rate Limit / Quota
| 変数 | 既定 | 説明 |
|---|---|---|
| `RL_RATE_PER_MIN` | `60` | 1分窓上限 |
| `RL_BURST` | `30` | バースト |
| `DAILY_QUOTA` | `10000` | 日次上限 |

---

## 6. ブローカー
| 変数 | 既定 | 説明 |
|---|---|---|
| `BROKER_ADAPTER` | `paper` | `paper` / 実アダプタ名 |
| `BROKER_TIMEOUT_MS` | `2500` | 送信タイムアウト |
| `BROKER_API_KEY` | なし | 資格情報 |
| `BROKER_API_SECRET` | なし | 資格情報 |

---

## 7. 可観測性
| 変数 | 既定 | 説明 |
|---|---|---|
| `METRICS_PORT` | `9100` | Prometheus エンドポイント |
| `TRACE_ENABLED` | `false` | トレースON/OFF |
| `TRACE_EXPORTER` | なし | OTLP 等 |

---

## 8. 変更履歴
- **2025-08-24**: 初版
