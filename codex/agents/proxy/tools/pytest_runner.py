from __future__ import annotations
import subprocess, json, shlex
from pathlib import Path
from typing import Dict, Any

class PytestTool:
    name = "pytest"
    def __init__(self, cwd: str, reports_dir: Path):
        self.cwd = cwd
        self.reports_dir = reports_dir

    def run(self, **kwargs) -> Dict[str, Any]:
        args = kwargs.get("args", ["-q"])
        # ここでは既存の mini-loop が吐く tmp.json までは期待せず、簡易的にリターン
        cp = subprocess.run(["pytest", *args], cwd=self.cwd, capture_output=True, text=True)
        out = {"ok": cp.returncode == 0, "returncode": cp.returncode}
        # 失敗数だけでも推定
        failed = 0
        for line in cp.stderr.splitlines() + cp.stdout.splitlines():
            if line.strip().startswith("FAILED "):
                try:
                    failed = int(line.split()[1].split("failed")[0])
                except Exception:
                    pass
        out["failed"] = failed
        # ログ保存（短いファイル）
        (self.reports_dir / "proxy_pytest_last.log").write_text(cp.stdout + "\n" + cp.stderr)
        return out
