#!/bin/bash
set -e

CPU_PACKAGES_FILE="$1"

if [[ ! -f "$CPU_PACKAGES_FILE" ]]; then
  echo "[ERROR] Package list file not found: $CPU_PACKAGES_FILE"
  exit 1
fi

echo "[INFO] Installing system packages from: $CPU_PACKAGES_FILE"
apt-get install -y $(cat "$CPU_PACKAGES_FILE")
echo "[INFO] System packages installed!"
