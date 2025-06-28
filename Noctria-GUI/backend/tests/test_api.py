from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Noctria Backend is running"}

def test_get_config():
    response = client.get("/config")
    assert response.status_code == 200
    # デフォルト設定が返ることを確認
    config = response.json()
    assert "error_penalty_weight" in config
