#!/bin/bash

echo "🛠 Noctria Kingdom - Veritas GUI変更をコミット中..."

# === upload_history ルート
git add noctria_gui/routes/upload_history.py
git commit -m "✨ /upload-history に再評価・削除機能を追加（POST対応）"

# === upload_history テンプレート
git add noctria_gui/templates/upload_history.html
git commit -m "💄 GUIに再評価ボタン・削除ボタンを追加（/upload-history）"

# === upload_actions サービス層
git add noctria_gui/services/upload_actions.py
git commit -m "🧠 upload_actions.py 新設：戦略の再評価・削除を実装"

# === main.py ルータ登録
git add noctria_gui/main.py
git commit -m "🔗 upload_history ルートを GUIメインルータに統合（再評価・削除対応）"

# === templates/navbar.html（ナビゲーション統合）
git add noctria_gui/templates/components/navbar.html
git commit -m "🧭 GUIナビゲーションに /upload-history タブを統合"

# === その他未コミット分があれば表示
echo "📌 以下の変更は未コミットのままです："
git status --short

# === GitHub へ Push
read -p "🚀 変更をGitHubにPushしますか？ [y/N]: " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
  git push
  echo "✅ Push完了しました。王国の叡智がGitHubへ刻まれました。"
else
  echo "📝 Pushはキャンセルされました。"
fi
