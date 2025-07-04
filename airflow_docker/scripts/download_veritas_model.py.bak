from huggingface_hub import snapshot_download
import os

# 環境変数からHFトークンを取得（事前に .env に設定済み）
HF_TOKEN = os.getenv("HF_TOKEN", "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")

# 保存先ディレクトリ（Airflow/Dockerマウントパスと一致させる）
TARGET_DIR = "/mnt/e/noctria-kingdom-main/airflow_docker/models/nous-hermes-2"

# モデルダウンロード
snapshot_download(
    repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO",
    local_dir=TARGET_DIR,
    local_dir_use_symlinks=False,
    token=HF_TOKEN
)

print(f"✅ モデルを {TARGET_DIR} にダウンロードしました")
