import logging

logging.basicConfig(
    filename="logs/system.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_violation(message):
    """ ルール違反を記録 """
    logging.warning(f"Violation Detected: {message}")

log_violation("Trade rejected due to daily loss limit exceeded")
