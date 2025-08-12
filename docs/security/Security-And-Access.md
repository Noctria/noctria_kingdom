# 🔐 Security & Access — Noctria Kingdom

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の PDCA/運用全体に対して **最小権限・監査可能・回復可能** なセキュリティ基盤を定義する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../observability/Observability.md` / `../apis/API.md` / `../apis/Do-Layer-Contract.md`

---

## 1. スコープ & 原則
- スコープ：**API/GUI、Airflow、Plan/Do/Check/Act、データ/モデル、Secrets、ネットワーク、監査**  
- 原則：
  1) **最小権限（Least Privilege）** — 役割ベースで必要最低限のみ付与  
  2) **ゼロトラスト** — ネットワーク境界を信用しない（AuthN/Z & TLS）  
  3) **Secrets をコード/レポに残さない** — Vault/ENV 専用  
  4) **監査可能性** — 変更・実行・アクセスの**証跡**を保存  
  5) **二人承認** — 重大変更は **Two-Person Rule**（レビュー＋King 承認）  

---

## 2. データ分類 & 取り扱い
| クラス | 例 | 保存 | 転送 | ログ出力 |
|---|---|---|---|---|
| S3（機密） | APIキー、ブローカー認証、個人識別情報 | Vault/ENV（暗号化・厳格ACL） | TLS1.2+ | **禁止**（hash/伏字のみ） |
| S2（内部） | 戦略メタ、評価レポート、監査ログ | 暗号化ストレージ（KMS） | TLS1.2+ | **最小限**（body_hash） |
| S1（公開可） | リリースノート、設計資料 | Git | HTTPS | 可 |

> ログには **PII/Secrets を禁止**。必要時は **hash/伏字**（`Observability.md §12`）。

---

## 3. 役割と権限（RBAC）
| ロール | 主な権限 | 禁止事項 |
|---|---|---|
| **King** | 最終承認、Flags/Config の最終適用、緊急停止 | 直接Secrets閲覧（原則） |
| **Ops** | デプロイ、Airflow運用、抑制/再開、バックフィル | リスク境界の単独変更 |
| **Risk (Noctus)** | リスク境界設定、Safemode、アラート裁定 | デプロイ/Secrets編集 |
| **Models** | 学習/推論DAG、モデル登録 | 本番抑制制御 |
| **Arch** | スキーマ/契約変更、DAG設計レビュー | 本番Flagsの単独変更 |
| **ReadOnly** | ダッシュボード/ログ閲覧 | 書き込み全般 |

**アクセス申請フロー（概念）**
```mermaid
flowchart LR
  U[申請者] --> R[所属Leadレビュー]
  R --> S[Secレビュー(最小権限/期間設定)]
  S --> K[King承認]
  K --> I[適用(Vault/ACL/RBAC)]
  I --> A[監査記録]
```

---

## 4. 認証・認可（API/GUI）
- **Auth**：OIDC/JWT（GUI/外部）、内部トークン（サービス間）  
- **Scopes（例）**：`read:pdca`, `write:orders`, `read:config`, `write:config`, `admin:ops`  
- **2FA**：GUI 操作は 2FA 必須（`Config-Registry.md gui.auth.require_2fa`）  
- **CORS**：最小オリジン許可、Cookie利用時は `SameSite=strict`  
- **Rate Limit**：既定 60 rpm、`/do/orders` 系は 10 rps（`API.md §14`）

**API セキュアヘッダ（必須）**
- `Authorization: Bearer <JWT>` / `Noctria-Token <key>`  
- `Idempotency-Key`（変更系）  
- `X-Correlation-ID`（全リクエスト）

---

## 5. Secrets 管理
- 保存：**Vault/Secrets Backend/ENV**（Git/Variables へ保存禁止）  
- 参照：サービス起動時に**注入**（環境変数 or マウントファイル）  
- ローテーション：**90日**（`Runbooks.md §10`）／漏えい疑義時は即時  
- 監査：**誰が/いつ/何に**アクセスしたかを SIEM へ転送  
- 検査：PR時に **Secret Scan**（キーワード・entropy）を強制

**.env.sample（例）**
```dotenv
BROKER_API_KEY=
BROKER_API_SECRET=
DB_PRIMARY_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
```

---

## 6. Airflow のセキュリティ
- Web 認証：OIDC or Basic（**匿名閲覧禁止**）  
- RBAC：Viewer/Op/Model/Risk/King の**ロールに準拠**  
- Variables：**Secretsを置かない**（Connections/Secrets Backend を使用）  
- 接続情報：パスワードは**常にマスク**（Export禁止）  
- 実行権限：`max_active_runs`, `pools` で Do 層を**隔離**（影響限定）  
- 監査：Web UI 操作ログを保存（インポートエラー含む）

---

## 7. ネットワーク & 暗号化
- **TLS1.2+** を必須化（内部通信含む）  
- **最小開口**：外部に出すポートは API/GUI のみ。Airflow Web は管理ネットに限定  
- **Egress 制御**：ブローカー/API 宛のみ許可（Do 層）  
- **IP 制限**：本番 GUI/API は許可リスト制（必要に応じ VPN）  
- **At-Rest**：ストレージ暗号化（KMS）／バックアップも暗号化  
- **DNS/時刻**：NTP固定、Clock Skew 監視（`Risk-Register.md R-05`）

---

## 8. 変更管理 & Two-Person Rule
- **対象**：`risk_policy`/`flags`/`Do-Layer`/`API`/`Schemas`/`Observability Rules`  
- **運用**：**同一PR**で関連ドキュメントを更新（`Runbooks`/`Config-Registry`/`API`/`Do-Layer-Contract`）  
- **承認**：ロールごとに**二人承認 + King**（重大変更）  
- **ADR**：本質的変更は `../adrs/` に Decision/Context/Consequences を記録

---

## 9. 監査 & ログ（不可侵性）
- **統一フォーマット**：構造化 JSON（`Observability.md §3.1`）  
- **重要イベント**：`who/what/when/where` を必須（`correlation_id` 付与）  
- **tamper-evident**：監査ログは**改変検知**ストレージ（WORM 相当）へも保存推奨  
- **保持**：S2=90日以上、S3=最小限（法令・契約に従う）

---

## 10. インシデント対応（要点）
1) **検知**：アラート/通報/監査ログ  
2) **封じ込め**：`global_trading_pause`、アクセストークン無効化、回線遮断  
3) **根本原因**：トレース・監査・変更履歴の照合  
4) **回復**：段階再開（Safemode/低ロット）  
5) **報告**：24h 内に `../incidents/Incident-Postmortems.md` 草案  
6) **再発防止**：`Risk-Register.md` と `ADRs/` 更新

---

## 11. テンプレ & 手順

### 11.1 権限付与（期限付き）
```md
# Access Grant — {User} ({Role})
- 目的: {運用/調査/対応}
- 期間: {開始〜終了 JST}
- 最小権限: {role, scopes}
- 審査: Sec, 所属Lead
- 承認: King
- 設定: Vault/ACL/RBAC 反映済（証跡ID: ...）
- 失効手順: 自動失効 or 手動revoke（日時）
```

### 11.2 オンボーディング/オフボーディング チェックリスト
```md
## Onboarding
- [ ] NDA/ポリシー同意
- [ ] アカウント発行（OIDC）
- [ ] ロール割当（最小権限）
- [ ] 2FA 設定
- [ ] 監査に基づく初回ログイン確認

## Offboarding
- [ ] アカウント無効化
- [ ] Secrets/権限の revoke
- [ ] 端末・鍵の回収
- [ ] 監査/退職ログの保存
```

### 11.3 設定の安全サンプル（抜粋）
```yaml
gui:
  auth:
    provider: "oidc"
    require_2fa: true
observability:
  alerts:
    dag_fail_rate_pct: 5
flags:
  global_trading_pause: false
  risk_safemode: true
```

---

## 12. よくある質問（FAQ）
- **Q:** 変更加えるだけで King 承認いる？  
  **A:** `risk_policy`/`flags`/`Do-Layer`/`API`/`Schemas` は **Yes**。他はRACI表に従う。  
- **Q:** Airflow Variables にキーを入れてもいい？  
  **A:** **No**。Connections/Secrets Backend を使う。  
- **Q:** 誰が抑制を解除できる？  
  **A:** `Ops` が提案、`Risk` が評価、**King が最終承認**（`Runbooks §6` 併記）。

---

## 13. 既知の制約 / TODO
- VPN/Zero-Trust Network Access（ZTNA）導入の検討  
- Secrets ローテの自動化（回転と影響波及の可視化）  
- 監査ログの WORM ストレージ化（法規要件に合わせる）

---

## 14. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（RBAC/Secrets/ネットワーク/監査/Incident/Two-Person）

