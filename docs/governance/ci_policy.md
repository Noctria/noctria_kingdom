# CI Policy (暫定運用)

## 目的
- GitHub Free/Private プランの制約下でも、最低限の品質ゲートを担保する。
- Lint（コード規約）と Review（人の目）を必須化し、壊れたコードや独断マージを防止する。

---

## 現在の必須チェック
- `lint / ruff`  
  - Ruff lint (`ruff check --force-exclude src/core`) を実行。
- `lint / ruff-format`  
  - Ruff format (`ruff format --check --force-exclude src/core`) を実行。
- `pr-policy`  
  - 必須チェック未通過の PR を自動クローズ（Branch Protection 非対応の暫定措置）。
- `CODEOWNERS`  
  - `src/core/**` の変更には @Noctria の承認が必須。

---

## 運用ルール
1. **PR作成時**
   - Lint 未通過の場合は自動的に PR がクローズされる。
   - Lint 通過の場合でも、必ず CODEOWNERS レビューが必要。

2. **Merge条件**
   - Lint ✅  
   - Format ✅  
   - Review ✅  
   → すべて満たした場合のみマージ可能。

3. **レビューの扱い**
   - CODEOWNERS により `/src/core/**` の変更は必ず @Noctria のレビューが要求される。
   - 将来共同開発者が増えた場合は Org Team に切り替える。

---

## 将来移行
- **GitHub Pro or Public リポジトリ**に移行した場合:
  - 公式の Branch Protection を有効化。  
  - `pr-policy.yml`（自動クローズワークフロー）は廃止可能。  
  - CI 必須チェックとして `ruff` / `ruff-format` / `smoke` を設定。

---

## 拡張予定
- `smoke` テストの追加（tests/smoke 配下）。  
  - 主要モジュールが import できるか簡易検証。  
- ルール強化（段階的に E501, SIM, UP, B などを導入）。  
- jobs.name の整理（UIでの表示を `lint / ruff` / `lint / ruff-format` に統一）。

---

## チートシート
```bash
# 変更を lint にかける
pre-commit run -a

# lint 修正後にコミット
git add -A && git commit -m "fix: lint"
git push -u origin <branch>

# CI 設定変更例
git checkout -b ci/tune-ruff-names
vim .github/workflows/lint.yml
git commit -m "ci(lint): add job display names"
git push -u origin HEAD
