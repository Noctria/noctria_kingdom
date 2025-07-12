# noctria_gui/routes/__init__.py

import noctria_gui.routes.act_history
import noctria_gui.routes.act_history_detail
import noctria_gui.routes.dashboard
# その他のルートモジュールもインポート

routers = [
    noctria_gui.routes.act_history.router,
    noctria_gui.routes.act_history_detail.router,
    noctria_gui.routes.dashboard.router,
    # その他のルータを追加
]

