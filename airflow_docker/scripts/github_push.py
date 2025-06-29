import os
import subprocess

def main():
    token = os.getenv("GITHUB_PAT")
    if not token:
        raise ValueError("❌ GITHUB_PATが環境変数に設定されていません")

    repo_url = f"https://Noctria:{token}@github.com/Noctria/noctria_kingdom.git"
    commands = [
        ["git", "config", "--global", "user.email", "veritas@noctria.ai"],
        ["git", "config", "--global", "user.name", "Veritas Machina"],
        ["git", "add", "strategies/official/"],
        ["git", "commit", "-m", "🤖 Veritas戦略をofficialに自動反映"],
        ["git", "remote", "set-url", "origin", repo_url],
        ["git", "push", "origin", "main"]
    ]

    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"💻 {' '.join(cmd)}")
        if result.returncode != 0:
            print(f"⚠️ Error: {result.stderr}")
        else:
            print(f"✅ {result.stdout.strip()}")

if __name__ == "__main__":
    main()
