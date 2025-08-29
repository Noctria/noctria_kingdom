# 例: noctria_gui/main.py
from flask import Flask
from noctria_gui.routes.obs_latency_dashboard import bp_obs_latency

def create_app():
    app = Flask(__name__)
    # 既存の Blueprint 登録 …（省略）
    app.register_blueprint(bp_obs_latency)  # ← 追加
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
