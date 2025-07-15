#!/usr/bin/env python3
# coding: utf-8

import json
from typing import Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: 正しいインポートパスに修正
from src.core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="2.0.0",
)

# ========================================
# 📁 静的ファイルとテンプレートの登録
# ========================================
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2 カスタムフィルタ
def from_json(value: str) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
templates.env.filters["from_json"] = from_json

# ========================================
# 🏛️ 全ルート（機能）のインポート
# ========================================
from noctria_gui.routes import (
    dashboard, home_routes, king_routes, logs_routes,
    path_checker, trigger, upload, upload_history,
    act_history, act_history_detail,
    pdca, pdca_recheck, pdca_routes, pdca_summary,
    prometheus_routes, push,
    statistics_dashboard, statistics_detail, statistics_ranking,
    statistics_scoreboard, statistics_tag_ranking, statistics_compare,
    strategy_detail, strategy_heatmap, strategy_routes,
    tag_heatmap, tag_summary, tag_summary_detail
)

# ========================================
# 🔁 ルーター登録（機能ごとのグループ化）
# ========================================
print("Integrating all routers into the main application...")

# --- 基本ルート ---
app.include_router(home_routes.router)
app.include_router(dashboard.router)
app.include_router(king_routes.router)
app.include_router(trigger.router)

# --- ログ・履歴関連 ---
app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(logs_routes.router)
app.include_router(upload_history.router)

# --- PDCA・Push関連 ---
app.include_router(pdca.router)
app.include_router(pdca_recheck.router)
app.include_router(pdca_routes.router)
app.include_router(pdca_summary.router)
app.include_router(push.router)

# --- 戦略(Strategy)関連 ---
app.include_router(strategy_routes.router, prefix="/strategies", tags=["strategies"])
app.include_router(strategy_detail.router)
app.include_router(strategy_heatmap.router)

# --- 統計(Statistics)・サマリー関連 ---
app.include_router(statistics_dashboard.router, prefix="/statistics", tags=["statistics"])
app.include_router(statistics_detail.router)
app.include_router(statistics_ranking.router)
app.include_router(statistics_scoreboard.router)
app.include_router(statistics_tag_ranking.router)
app.include_router(statistics_compare.router)
app.include_router(tag_summary.router)
app.include_router(tag_summary_detail.router)
app.include_router(tag_heatmap.router)

# --- その他 ---
app.include_router(path_checker.router)
app.include_router(prometheus_routes.router)
app.include_router(upload.router)

print("✅ All routers have been integrated successfully.")

# ========================================
# ✨ 便利機能
# ========================================
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """ブラウザのfavicon.icoリクエストに対する404エラーを抑制するための空のレスポンス"""
    return Response(status_code=204)

