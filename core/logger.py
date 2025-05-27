import logging

def setup_logger(name, level=logging.INFO):
    """指定した名前でロガーを設定する"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

# ✅ サンプルログのテスト
if __name__ == "__main__":
    logger = setup_logger("NoctriaLogger")
    logger.info("Noctria Kingdom logging system initialized.")
