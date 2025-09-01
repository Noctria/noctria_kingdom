from __future__ import annotations
from pathlib import Path
from .core import Agent, Policy, Task
from .tools.fs import FSTool
from .tools.git import GitTool
from .tools.pytest_runner import PytestTool

def main() -> int:
    root = Path(__file__).resolve().parents[3]  # PROJECT_ROOT
    reports = root / "codex_reports"
    reports.mkdir(exist_ok=True, parents=True)

    agent = Agent(
        tools={
            "fs": FSTool(root),
            "git": GitTool(str(root)),
            "pytest": PytestTool(str(root), reports),
        },
        policy=Policy(),
    )
    res = agent.run_task(Task(kind="apply-generated-patches", payload={}))
    (reports / "proxy_last_result.json").write_text(__import__("json").dumps(res, ensure_ascii=False, indent=2))
    print(res)
    return 0 if res.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
