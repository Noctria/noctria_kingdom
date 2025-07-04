#!/bin/bash
set -e

PYTHON_VERSION="$1"
REQUIREMENTS_FILE="$2"

if [[ -z "$PYTHON_VERSION" || -z "$REQUIREMENTS_FILE" ]]; then
  echo "[ERROR] Usage: $0 <python_version> <requirements_file>"
  exit 1
fi

echo "[INFO] Setting up Python environment..."
update-alternatives --install /usr/bin/python python /usr/bin/$PYTHON_VERSION 1

echo "[INFO] Upgrading pip..."
pip install --upgrade pip

echo "[INFO] Installing Python dependencies from: $REQUIREMENTS_FILE"
pip install -r "$REQUIREMENTS_FILE"

echo "[INFO] Python environment ready!"
