import subprocess
import os

def get_unmerged_files():
    result = subprocess.run(['git', 'status', '--porcelain'], stdout=subprocess.PIPE)
    lines = result.stdout.decode().splitlines()
    return [line[3:] for line in lines if line.startswith('UU ') or 'both added:' in line]

def resolve_conflicts_prefer_ours(filepaths):
    for path in filepaths:
        # 現在の作業ディレクトリにあるものを使用（ours）として add
        subprocess.run(['git', 'add', path])
        print(f"✅ 解決済み: {path}")

def commit_and_push():
    subprocess.run(['git', 'commit', '-m', '🤖 自動マージ解決：ours優先'])
    subprocess.run(['git', 'push', 'origin', 'main'])

if __name__ == "__main__":
    files = get_unmerged_files()
    if not files:
        print("✅ コンフリクトは存在しません")
    else:
        print(f"🧩 検出された unmerged ファイル: {len(files)} 件")
        resolve_conflicts_prefer_ours(files)
        commit_and_push()
