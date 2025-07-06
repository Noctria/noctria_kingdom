#!/usr/bin/env python3
# coding: utf-8

"""
🔗 Noctria GUI ルート統合モジュール
- 各ページ用ルーターの一括読み込みと登録
"""

from . import home_routes
from . import strategy_routes
from . import pdca
from . import upload
from . import upload_history
from . import act_history
from . import act_history_detail
from . import push_history
from . import strategy_compare

# ルートを app.include_router() で登録する側（main.py）から読み込まれる前提
routers = [
    home_routes.router,
    strategy_routes.router,
    pdca.router,
    upload.router,
    upload_history.router,
    act_history.router,
    act_history_detail.router,
    push_history.router,
    strategy_compare.router,
]
