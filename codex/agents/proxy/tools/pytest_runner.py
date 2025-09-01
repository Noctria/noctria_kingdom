# codex/agents/proxy/tools/pytest_runner.py
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Any


class PytestTool:
    """
    pytest 実行ラッパ。
    - rc==0: "passed"
    - rc==5: "no-tests"
    - rc==1: "failed:{n}"
    - それ以外: "error:rc={rc}"
    常に PYTHONPATH に [プロジェクトルート, src/] を追加して収集安定化。
    """
    name = "pytest"

    def __init__(self, cwd: str, reports_dir: Path):
        self.cwd = cwd
        self.reports_dir = reports_dir

    def run(self, **kwargs) -> Dict[str, Any]:
        args = kwargs.get("args", ["-q"])

        env = os.environ.copy()
        proj = Path(self.cwd).resolve()
        extra = [str(proj), str(proj / "src")]
        current = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        for e in extra:
            if e not in current:
                current.append(e)
        env["PYTHONPATH"] = os.pathsep.join(current)

        cp = subprocess.run(["pytest", *args], cwd=self.cwd, env=env,
                            capture_output=True, text=True)
        rc = cp.returncode

        # 失敗数の推定
        failed = 0
        try:
            import re
            for line in (cp.stderr.splitlines() + cp.stdout.splitlines()):
                m = re.search(r"(\d+)\s+failed", line.lower())
                if m:
                    failed = int(m.group(1))
                    break
        except Exception:
            pass

        if rc == 0:
            ok, status = True, "passed"
        elif rc == 5:
            ok, status = True, "no-tests"
        elif rc == 1:
            ok, status = False, f"failed:{failed}"
        else:
            ok, status = False, f"error:rc={rc}"

        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            (self.reports_dir / "proxy_pytest_last.log").write_text(
                (cp.stdout or "") + "\n" + (cp.stderr or ""),
                encoding="utf-8",
            )
        except Exception:
            pass

        return {"ok": ok, "returncode": rc, "failed": failed, "status": status}
