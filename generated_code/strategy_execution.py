import logging
from src.core.king_noctria import execute_order

def generate_trade_signal(predictions):
    """Generate trading signals based on model predictions."""
    try:
        # Example signal generation logic
        signals = ['BUY' if pred > 0 else 'SELL' for pred in predictions]
        return signals
    except Exception as e:
        logging.error(f"Error generating trade signals: {e}")
        raise

def execute_strategy(signals):
    """Execute trading strategy based on signals."""
    try:
        for signal in signals:
            execute_order(signal)
    except Exception as e:
        logging.error(f"Error executing strategy: {e}")
        raise
