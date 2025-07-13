#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes.statistics
- 統計系ルート群（ランキング・比較・詳細など）を統合登録
"""

from fastapi import APIRouter

# 📊 各サブルートをインポート
from . import statistics_ranking
from . import statistics_detail
from . import strategy_compare  # ✅ 統計比較フォーム & 結果（/compare/form, /compare/render）

# 🔗 統合ルーターを作成
router = APIRouter()
router.include_router(statistics_ranking.router)      # 🥇 タグ別ランキング
router.include_router(statistics_detail.router)       # 📋 個別詳細分析
router.include_router(strategy_compare.router)        # ⚔️ 戦略比較フォーム＋結果
