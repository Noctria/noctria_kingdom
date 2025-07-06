#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動スクリプト
- FastAPIにより王国の統治パネルを展開
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

# ✅ 統治下の正式パス
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ 統治ルートの招集
from noctria_gui.routes import (
    home_routes,
    strategy_routes,
    strategy_detail,
    strategy_compare,         # 📊 戦略比較
    tag_summary,
    tag_summary_detail,
    tag_heatmap,              # 🔥 タグ × 指標ヒートマップ
    statistics,               # 📈 統計スコアボード
    act_history,              # 📜 昇格戦略ログ
    act_history_detail,       # 📄 昇格ログの詳細表示
    push_history,             # 📦 GitHub Pushログ
    upload,                   # ⬆️ 戦略アップロード
    upload_history,           # 🧭 アップロード履歴
    pdca                      # 🔁 PDCAダッシュボード
)

# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================

app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# ✅ 静的ファイルとテンプレートの登録
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2 カスタムフィルタ：from_json（文字列 → dict）
def from_json(value: str):
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json

# ✅ テンプレート環境を app.state に格納（共通アクセス用）
app.state.templates = templates

# ✅ 各ルートを FastAPI アプリに結合
app.include_router(home_routes.router)
app.include_router(strategy_routes.router)
app.include_router(strategy_detail.router)
app.include_router(strategy_compare.router)     # 📊 /strategies/compare
app.include_router(tag_summary.router)
app.include_router(tag_summary_detail.router)
app.include_router(tag_heatmap.router)          # 🔥 /tag-heatmap
app.include_router(statistics.router)           # 📈 /statistics
app.include_router(act_history.router)          # 📜 /act-history
app.include_router(act_history_detail.router)   # 📄 /act-history/detail
app.include_router(push_history.router)         # 📦 /push-history
app.include_router(upload.router)
app.include_router(upload_history.router)
app.include_router(pdca.router)                 # 🔁 /pdca
