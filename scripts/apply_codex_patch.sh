# scripts/apply_codex_patch.sh
#!/usr/bin/env bash
set -euo pipefail

PATCH_FILE="${1:-}"
if [[ -z "$PATCH_FILE" ]]; then
  echo "Usage: scripts/apply_codex_patch.sh <path/to.patch>"
  exit 1
fi
if [[ ! -f "$PATCH_FILE" ]]; then
  echo "Patch not found: $PATCH_FILE"
  exit 1
fi

echo "Applying patch: $PATCH_FILE"
git apply --index "$PATCH_FILE"
echo "Patch staged. You can 'git commit -m \"Codex patch\"' now."
