# src/scripts/try_hermes_cognitor.py
from src.strategies.hermes_cognitor import HermesCognitorStrategy


def main():
    hermes = HermesCognitorStrategy()

    features = {"price": 152.3, "volume": 180, "volatility": 0.12}
    labels = ["買い圧力", "短期MA上抜け"]
    reason = "smoke_test"

    res = hermes.propose(
        {"features": features, "labels": labels, "reason": reason, "trace_id": "TEST-HERMES"}
    )
    print("=== Hermes result ===")
    for k, v in res.items():
        print(k, ":", v)


if __name__ == "__main__":
    main()
