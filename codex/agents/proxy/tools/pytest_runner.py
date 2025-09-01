cat > codex/agents/proxy/tools/pytest_runner.py << 'PY'
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Any


class PytestTool:
    """
    pytest 実行ラッパ（代理AI/CI 安定運用版）

    - 常に PYTHONPATH に [プロジェクトルート, src/] を追加
    - 既定で tests/ のみ収集（tests が無ければプロジェクト全体）
    - addopts は pytest.ini / PYTEST_ADDOPTS を尊重しつつ、指定が無ければ [-q, --maxfail=1] を補完
    - 終了コードを厳密分類:
        rc==0 -> "passed"
        rc==5 -> "no-tests"
        rc==1 -> "failed:{n}"
        それ以外 -> "error:rc={rc}"
    - ログは codex_reports/proxy_pytest_last.log に保存
    - デフォルト timeout=180s（kwargs["timeout"] で上書き可）
    """
    name = "pytest"

    def __init__(self, cwd: str, reports_dir: Path):
        self.cwd = cwd
        self.reports_dir = reports_dir

    def _build_env(self) -> dict:
        env = os.environ.copy()
        proj = Path(self.cwd).resolve()
        # PYTHONPATH に [proj, proj/src] を追加
        extra = [str(proj), str(proj / "src")]
        current = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        for e in extra:
            if e not in current:
                current.append(e)
        env["PYTHONPATH"] = os.pathsep.join(current)
        return env

    def _default_args(self) -> list[str]:
        args: list[str] = []

        # pytest.ini / 環境が addopts を提供しない場合のデフォルト補完
        addopts_env = os.environ.get("PYTEST_ADDOPTS", "").strip()
        if not addopts_env:
            args += ["-q", "--maxfail=1"]

        # 収集対象: tests/ があればそこに限定
        tests_dir = Path(self.cwd) / "tests"
        if tests_dir.is_dir():
            args.append(str(tests_dir))
        return args

    def run(self, **kwargs) -> Dict[str, Any]:
        # 追加引数（例: ["-k", "not integration"]）を外から渡せる
        extra_args = kwargs.get("args") or []
        timeout = int(kwargs.get("timeout") or 180)

        env = self._build_env()
        base_args = self._default_args()
        cmd = ["pytest", *base_args, *extra_args]

        cp = subprocess.run(
            cmd,
            cwd=self.cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
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

        return {"ok": ok, "returncode": rc, "failed": failed, "status": status, "cmd": " ".join(cmd)}
PY
