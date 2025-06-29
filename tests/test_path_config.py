# tests/test_path_config.py

from core import path_config
from pathlib import Path

def test_path_definitions():
    print("🔍 Testing path_config.py paths...\n")

    global_vars = dict(globals())  # 🔧 変更されないようコピー
    for name, path in global_vars.items():
        if name.endswith("_DIR") or name.endswith("_LOG"):
            if isinstance(path, Path):
                print(f"{name:30} → {path.resolve()}")
            else:
                print(f"{name:30} → {path}")

if __name__ == "__main__":
    test_path_definitions()
