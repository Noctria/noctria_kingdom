#!/usr/bin/env python3
# coding: utf-8
"""
📌 Decision Minidemo

- This module serves as an entry point for the decision minidemo.
"""

from __future__ import annotations

import os
import sys

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decision.decision_engine import DecisionEngine


def main():
    # Initialize the decision engine
    engine = DecisionEngine()
    proposals = []  # Default to an empty list if no proposals are provided
    req = {}  # Replace with actual request data as needed

    # Call the decide method with the proposals
    result = engine.decide(req, proposals)
    print(result)


if __name__ == "__main__":
    main()
