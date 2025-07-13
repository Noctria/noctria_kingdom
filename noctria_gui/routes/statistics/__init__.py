#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes.statistics
- 統計系ルート群（ランキング・比較・詳細など）を統合登録
"""

from fastapi import APIRouter
from . import statistics_ranking
from . import statistics_detail
from ..strategy_compare import router as strategy_compare_router  # ← 追加ポイント

router = APIRouter()
router.include_router(statistics_ranking.router)
router.include_router(statistics_detail.router)
router.include_router(strategy_compare_router)  # ✅ 統計比較ルートを統合
