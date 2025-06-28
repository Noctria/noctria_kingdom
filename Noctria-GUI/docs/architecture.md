# Noctria GUI システムアーキテクチャ

このドキュメントでは、Noctria GUI 管理・監視ツールのアーキテクチャおよび設計方針について記述します。

## コンポーネント構成

- **バックエンド (FastAPI):** API と WebSocket で設定およびログデータを提供
- **フロントエンド (Streamlit):** 管理ダッシュボード、設定変更、リアルタイムモニタリング
- **共有設定:** YAML 形式でのデフォルト設定管理
- **CI/CD:** GitHub Actions を用いた自動テスト・デプロイ

## 今後の拡張計画

- セキュリティ強化 (OAuth2 / JWT の導入)
- リアルタイム更新の改善 (WebSocket の導入)
- 運用監視の強化 (Grafana/Prometheus の連携)
