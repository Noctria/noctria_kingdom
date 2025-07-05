# =========================================
# 🏛 Noctria Kingdom Makefile (v1.0)
# =========================================

# === 環境変数（プロジェクトルートの.envを読み込む） ===
ENV_FILE = .env
include $(shell [ -f $(ENV_FILE) ] && echo $(ENV_FILE))

# === venv 名（必要に応じて変更） ===
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python3
PIP = $(VENV_DIR)/bin/pip

# === Docker 関連 ===
build-airflow:
	docker compose -f airflow_docker/docker-compose.yaml build

up-airflow:
	docker compose -f airflow_docker/docker-compose.yaml up -d

down-airflow:
	docker compose -f airflow_docker/docker-compose.yaml down

logs-airflow:
	docker compose -f airflow_docker/docker-compose.yaml logs -f

restart-airflow: down-airflow up-airflow

# === venv 関連 ===
venv-create:
	python3 -m venv $(VENV_DIR)

venv-install-veritas:
	$(PIP) install -r veritas/requirements_veritas.txt

venv-install-gui:
	$(PIP) install -r noctria_gui/requirements_gui.txt

venv-install-server:
	$(PIP) install -r llm_server/requirements_server.txt

venv-activate:
	@echo "source $(VENV_DIR)/bin/activate"

venv-clean:
	rm -rf $(VENV_DIR)

# === GitHub 操作 ===
git-pull:
	git pull origin main

git-push:
	git add .
	git commit -m "🔁 Update from Makefile"
	git push origin main

# === Veritas 戦略生成・評価 ===
generate-strategy:
	PYTHONPATH=$(PWD) $(PYTHON) veritas/generate_strategy_file.py

evaluate-strategy:
	PYTHONPATH=$(PWD) $(PYTHON) veritas/evaluate_veritas.py

# === 環境チェック ===
check-pythonpath:
	@echo "🔍 PYTHONPATH = $(PYTHONPATH)"
	@echo "🔍 Current Directory = $(PWD)"

# === その他 ===
help:
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
