#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  new-adopt)
    topic="${2:-adopt/work}"
    git switch main
    git pull --ff-only
    git switch -c "$topic"
    git push -u origin "$topic"
    echo "✅ created & tracked $topic"
    ;;

  sync-adopt)
    git fetch origin
    git merge --ff-only origin/main || git rebase origin/main
    echo "✅ synced $(git rev-parse --abbrev-ref HEAD) with origin/main"
    ;;

  pull-main)
    git switch main
    git pull --ff-only
    echo "✅ pulled main"
    ;;

  *)
    echo "Usage:
  bash scripts/git_playbook.sh new-adopt adopt/<topic>
  bash scripts/git_playbook.sh sync-adopt
  bash scripts/git_playbook.sh pull-main
"
    ;;
esac
