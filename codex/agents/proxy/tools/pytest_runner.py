# codex/agents/proxy/tools/pytest_runner.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Any


class PytestTool:
    """
    pytest を実行して結果を返す最小ラッパ。
    - returncode==0 → all passed
    - returncode==5 → no tests collected（成功扱いにする）
    - 失敗数は出力の要約行から推定（無ければ 0）
    - 直近の標準出力/標準エラーは codex_reports/proxy_pytest_last.log に保存
    """
    name = "pytest"

    def __init__(self, cwd: str, reports_dir: Path):
        self.cwd = cwd
        self.reports_dir = reports_dir

    def run(self, **kwargs) -> Dict[str, Any]:
        args = kwargs.get("args", ["-q"])
        cp = subprocess.run(["pytest", *args], cwd=self.cwd, capture_output=True, text=True)
        rc = cp.returncode

        # Pytest の戻り値:
        # 0: all tests passed
        # 1: tests failed
        # 2: usage error
        # 5: no tests collected  ← スモーク用途では成功扱い
        ok = (rc == 0 or rc == 5)

        # 失敗数の推定（例: "== 1 failed, 2 passed in 0.12s =="）
        failed = 0
        try:
            import re
            for line in (cp.stderr.splitlines() + cp.stdout.splitlines()):
                s = line.strip().lower()
                m = re.search(r"(\d+)\s+failed", s)
                if m:
                    failed = int(m.group(1))
                    break
        except Exception:
            # 推定失敗時は 0 のまま
            pass

        # ログ保存
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            (self.reports_dir / "proxy_pytest_last.log").write_text(
                (cp.stdout or "") + "\n" + (cp.stderr or ""),
                encoding="utf-8",
            )
        except Exception:
            pass

        return {
            "ok": ok,
            "returncode": rc,
            "failed": failed,
        }
