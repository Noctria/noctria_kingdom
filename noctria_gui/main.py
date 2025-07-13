# ========================================
# ルーターのインポート
# ========================================
from noctria_gui.routes import (
    dashboard, 
    home_routes,
    act_history,
    act_history_detail,
    king_routes,
    logs_routes,
    path_checker,
    pdca,
    pdca_recheck,
    pdca_routes,
    prometheus_routes,
    push,
    statistics,
    statistics_compare,
    statistics_detail,
    statistics_ranking,
    statistics_scoreboard,
    statistics_tag_ranking,
    statistics_dashboard,  # ← ✅ 追加ここ！
    strategy_compare,
    strategy_detail,
    strategy_heatmap,
    strategy_routes,
    tag_heatmap,
    tag_summary,
    upload,
    upload_history,
)

# ...（中略）

# 各機能ページのルーター
app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(king_routes.router)
app.include_router(logs_routes.router)
app.include_router(path_checker.router)
app.include_router(pdca.router)
app.include_router(pdca_recheck.router)
app.include_router(pdca_routes.router)
app.include_router(prometheus_routes.router)
app.include_router(push.router)
app.include_router(statistics.router)
app.include_router(statistics_compare.router)
app.include_router(statistics_detail.router)
app.include_router(statistics_ranking.router)
app.include_router(statistics_scoreboard.router)
app.include_router(statistics_tag_ranking.router)
app.include_router(statistics_dashboard.router)  # ← ✅ 追加ここ！
app.include_router(strategy_compare.router)
app.include_router(strategy_detail.router)
app.include_router(strategy_heatmap.router)
app.include_router(strategy_routes.router)
app.include_router(tag_heatmap.router)
app.include_router(tag_summary.router)
app.include_router(upload.router)
app.include_router(upload_history.router)
