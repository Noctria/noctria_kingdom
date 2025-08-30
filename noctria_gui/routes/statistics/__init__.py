# noctria_gui/routes/statistics/__init__.py

# このファイルは、statistics関連のルーターを外部に提供するための「窓口」です。
# 実際のURL処理は、statistics_dashboard.py に記述されています。

from .statistics_dashboard import router

# 上記の1行により、アプリケーションの他の部分（main.pyなど）が
# from noctria_gui.routes.statistics import router
# と書いた際に、正しく statistics_dashboard.py の機能が読み込まれるようになります。
