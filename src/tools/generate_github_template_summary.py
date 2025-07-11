import requests
import base64

# === 🔧 設定 ===
GITHUB_USER = "Noctria"
REPO_NAME = "noctria_kingdom"
BRANCH = "main"
GITHUB_TOKEN = "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"  # ← あなたのGitHubトークン（repo権限）

TARGET_DIRS = [
    "airflow_docker",
    "airflow_docker/dags",
    "airflow_docker/strategies",
    "airflow_docker/core",
    "airflow_docker/data",
    "veritas",
    "veritas_dev"
]

HEAD_LINES = 10
OUTPUT_FILE = "NOCTRIA_REMOTE_TEMPLATE.md"

# === 📦 GitHub API関数 ===
def fetch_tree(user, repo, branch, token):
    url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["tree"]

def fetch_file_content(user, repo, path, token):
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    if "content" in data:
        return base64.b64decode(data["content"]).decode("utf-8")
    return None

# === 📝 Markdownテンプレート生成 ===
def generate_summary():
    md = f"# 📘 Noctria Kingdom GitHub構成テンプレート（API自動生成）\n"
    md += f"対象リポジトリ: `{GITHUB_USER}/{REPO_NAME}` @ `{BRANCH}`\n\n"

    tree = fetch_tree(GITHUB_USER, REPO_NAME, BRANCH, GITHUB_TOKEN)

    for base in TARGET_DIRS:
        md += f"## 📁 `{base}/`\n"
        for obj in tree:
            if obj["type"] == "blob" and obj["path"].startswith(base) and obj["path"].endswith(".py"):
                rel_path = obj["path"]
                md += f"### 📄 `{rel_path}`\n```python\n"
                try:
                    content = fetch_file_content(GITHUB_USER, REPO_NAME, rel_path, GITHUB_TOKEN)
                    if content:
                        lines = content.splitlines()[:HEAD_LINES]
                        md += "\n".join(lines)
                except Exception as e:
                    md += f"# ⚠️ 読み込み失敗: {e}"
                md += "\n```\n\n"
        md += "\n"
    return md

# === 💾 メイン処理 ===
if __name__ == "__main__":
    summary = generate_summary()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ Markdownテンプレート生成完了: {OUTPUT_FILE}")
