# Generated actionable test for codex_task_20250926T174048_000000
import importlib


def test_main_create_app_returns_fastapi():
    mod = importlib.import_module("noctria_gui.main")
    assert hasattr(mod, "create_app"), "create_app() が存在しません"
    app = mod.create_app()
    # FastAPI を直接 import せず isinstance チェックを回避（依存軽量化）
    assert hasattr(app, "router") and hasattr(app, "openapi"), "FastAPI らしい属性がありません"


def test_health_endpoint_exists():
    mod = importlib.import_module("noctria_gui.main")
    app = mod.create_app()

    # 依存を増やさないため TestClient を使わず、ルーティング定義だけ検査
    # /healthz または / のどちらかが存在していること
    paths = set()
    for r in getattr(app.router, "routes", []):
        path = getattr(r, "path", "")
        if isinstance(path, str):
            paths.add(path)
    assert ("/healthz" in paths) or ("/" in paths), (
        f"ヘルスチェックまたは / がありません: {sorted(paths)}"
    )
