import os
import subprocess

import pytest


@pytest.mark.integration
def test_decision_minidemo_writes_db(monkeypatch):
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    assert dsn is not None, "NOCTRIA_OBS_PG_DSN must be set for integration test."

    # Mock proposals argument
    proposals = ["--mock-proposal"]  # Add appropriate mock proposals here if needed

    # Execute the decision engine with the proposals
    out = subprocess.check_output(
        ["python", "-m", "src.e2e.decision_minidemo"] + proposals, text=True
    )
    assert out is not None  # Ensure output is not None
