# -------------------------------------------------------------------
# File: src/core/git_utils.py
# -------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
Git 操作用の簡易ヘルパ
- 環境変数:
  GIT_REMOTE: 例 "origin"
  GIT_BRANCH: 例 "main"
  GIT_USER_NAME / GIT_USER_EMAIL: 未設定なら既存設定を利用
"""

import os
import subprocess
from typing import List, Optional

def _run(cmd: List[str], cwd: Optional[str] = None, check: bool = True) -> str:
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout

class GitHelper:
    def __init__(self, repo_dir: Optional[str] = None):
        self.repo_dir = repo_dir or os.getenv("GIT_REPO_DIR") or os.getcwd()
        self.remote = os.getenv("GIT_REMOTE", "origin")
        self.branch = os.getenv("GIT_BRANCH", "main")
        user = os.getenv("GIT_USER_NAME")
        email = os.getenv("GIT_USER_EMAIL")
        if user:
            _run(["git", "config", "user.name", user], cwd=self.repo_dir, check=False)
        if email:
            _run(["git", "config", "user.email", email], cwd=self.repo_dir, check=False)

    def add_commit_push(self, paths: List[str], message: str):
        _run(["git", "add"] + paths, cwd=self.repo_dir)
        # 変更がない場合もあるのでcommitはcheck=Falseで実施
        _run(["git", "commit", "-m", message], cwd=self.repo_dir, check=False)
        # 競合回避のため一応pull --rebase
        _run(["git", "pull", "--rebase", self.remote, self.branch], cwd=self.repo_dir, check=False)
        _run(["git", "push", self.remote, self.branch], cwd=self.repo_dir)

    def create_tag_and_push(self, prefix: str = "veritas", annotation: str = "") -> str:
        # タグ名: {prefix}-YYYYMMDD-HHMMSS
        import datetime
        tag = f"{prefix}-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        if annotation:
            _run(["git", "tag", "-a", tag, "-m", annotation], cwd=self.repo_dir)
        else:
            _run(["git", "tag", tag], cwd=self.repo_dir)
        _run(["git", "push", self.remote, tag], cwd=self.repo_dir)
        return tag
