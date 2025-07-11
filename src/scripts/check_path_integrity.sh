#!/bin/bash
# ==============================================
# 🛡️ Noctria Kingdom パス整合性検査ラッパー
# - path_config の構成ミスを事前検出
# ==============================================

echo "🧭 Noctria Kingdom: 路構図検査を開始します..."

# strict + path表示モードで検査実行
python3 tools/verify_path_config.py --strict --show-paths

# 検査結果の終了コード確認
if [ $? -ne 0 ]; then
  echo "❌ 王国の構成に不整合があります。修正を行ってから再試行してください。"
  exit 1
else
  echo "✅ 路構図は正しく整っています。王国の秩序は守られています。"
fi
