import os
import sys
import importlib
import logging
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Noctria_Debug")

# 1. プロジェクトのルートとsrcディレクトリの確認
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # プロジェクトルート
SRC_DIR = PROJECT_ROOT / "src"

logger.debug(f"PROJECT_ROOT: {PROJECT_ROOT}")
logger.debug(f"SRC_DIR: {SRC_DIR}")

# 2. sys.pathの整備と確認
logger.debug("Checking sys.path...")
sys.path.insert(0, str(SRC_DIR))
logger.debug(f"sys.path after update: {sys.path}")

# 3. `GUI_TEMPLATES_DIR` の設定確認
try:
    from src.core.path_config import GUI_TEMPLATES_DIR
    logger.debug(f"GUI_TEMPLATES_DIR: {GUI_TEMPLATES_DIR}")
except ImportError as e:
    logger.error(f"Error importing GUI_TEMPLATES_DIR: {e}")
    logger.debug("Checking available paths:")
    for path in sys.path:
        logger.debug(f"Path: {path}")

# 4. `path_config` のインポート確認
logger.debug("Checking if 'src.core.path_config' can be imported...")
try:
    importlib.import_module("src.core.path_config")
    logger.debug("src.core.path_config imported successfully")
except ImportError as e:
    logger.error(f"Error importing src.core.path_config: {e}")
    logger.debug("Attempting to print more details...")
    logger.debug(f"Current working directory: {os.getcwd()}")

# 5. GUI_TEMPLATES_DIR のディレクトリ確認
if 'GUI_TEMPLATES_DIR' in locals():
    if os.path.exists(GUI_TEMPLATES_DIR):
        logger.debug(f"GUI_TEMPLATES_DIR exists: {GUI_TEMPLATES_DIR}")
    else:
        logger.error(f"GUI_TEMPLATES_DIR does not exist: {GUI_TEMPLATES_DIR}")

# 6. `path_config.py` 内の重要なパスの存在確認
logger.debug("Checking key paths in path_config.py...")
paths_to_check = [
    "PROJECT_ROOT", "SRC_DIR", "NOCTRIA_GUI_TEMPLATES_DIR", "NOCTRIA_GUI_STATIC_DIR",
    "AIRFLOW_DOCKER_DIR", "DATA_DIR", "STATS_DIR", "VERITAS_DIR", "STRATEGIES_DIR"
]

for path_name in paths_to_check:
    path = globals().get(path_name)
    if path and isinstance(path, Path):
        if path.exists():
            logger.debug(f"{path_name} exists: {path}")
        else:
            logger.error(f"{path_name} does not exist: {path}")
    else:
        logger.warning(f"{path_name} is not defined or not a valid Path object")

# 7. ディレクトリとファイルの詳細確認（デバッグ用）
logger.debug("Checking if critical directories exist...")
critical_dirs = [
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "noctria_gui" / "templates",
    PROJECT_ROOT / "noctria_gui" / "static",
    SRC_DIR / "core",
]

for directory in critical_dirs:
    if directory.exists():
        logger.debug(f"Directory exists: {directory}")
    else:
        logger.error(f"Directory does not exist: {directory}")

# 8. `GUI_TEMPLATES_DIR` が設定された場合にファイルが存在するかをチェック
if 'GUI_TEMPLATES_DIR' in locals() and GUI_TEMPLATES_DIR:
    logger.debug(f"Checking template directory: {GUI_TEMPLATES_DIR}")
    template_files = list(GUI_TEMPLATES_DIR.glob("*.html"))
    if template_files:
        logger.debug(f"Templates found: {', '.join([str(f) for f in template_files])}")
    else:
        logger.error(f"No templates found in {GUI_TEMPLATES_DIR}")
