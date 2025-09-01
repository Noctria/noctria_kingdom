# codex/agents/proxy/tools/git.py
from __future__ import annotations

import shlex
import subprocess
from typing import Dict, Any, List


class GitTool:
    """
    安全サブセットの git 操作。
    - apply_patch(check_only=True/False): -p1 を指定して a/ b/ プレフィクスを剥がす
    - restore_worktree(): 追跡ファイルの変更を破棄 + 未追跡のうち keep_dirs は残す
    """
    name = "git"

    def __init__(self, cwd: str, keep_dirs: List[str] | None = None):
        self.cwd = cwd
        self.keep_dirs = keep_dirs or ["codex_reports/"]

    def _run(self, cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(shlex.split(cmd), cwd=self.cwd, capture_output=True, text=True)

    def run(self, **kwargs) -> Dict[str, Any]:
        act = kwargs.get("action")

        if act == "apply_patch":
            path = kwargs["path"]
            check = kwargs.get("check_only", False)
            # -p1 で a/ or b/ を剥がす。check_only 時は --check を併用
            cmd = f"git apply -p1 {'--check' if check else ''} {shlex.quote(path)}".strip()
            cp = self._run(cmd)
            if cp.returncode != 0:
                return {"ok": False, "error": (cp.stderr or cp.stdout).strip()}
            return {"ok": True}

        if act == "restore_worktree":
            # 追跡ファイルのローカル変更を破棄
            cp = self._run("git restore -SW .")
            if cp.returncode != 0:
                return {"ok": False, "error": (cp.stderr or cp.stdout).strip()}

            # 未追跡は keep_dirs を除外してクリーン
            exclude_args = ""
            for d in self.keep_dirs:
                dd = d if d.endswith("/") else d + "/"
                exclude_args += f" -e {dd} -e {dd}**"
            cp = self._run(f"git clean -fd{exclude_args}")
            if cp.returncode != 0:
                return {"ok": False, "error": (cp.stderr or cp.stdout).strip()}
            return {"ok": True}

        return {"ok": False, "error": f"unknown git action: {act}"}
