#!/usr/bin/env bash
# whetstone — daily lesson generator (cron entry point).
#
# Resolves the user's primary language, picks the topic, writes today's
# lesson file at ~/.whetstone/lessons/YYYY-MM-DD/, and opens it in VS Code.
#
# Called by launchd at 07:00 local time (see templates/launchd.plist),
# but safe to invoke directly any time. Pass --force to regenerate
# today's lesson even if one already exists.

set -euo pipefail

REPO="${WHETSTONE_REPO:-$HOME/whetstone}"
STATE="${WHETSTONE_STATE:-$HOME/.whetstone}"

if [[ ! -d "$STATE" ]]; then
  echo "✗ State directory $STATE not found. Run $REPO/scripts/install.sh first." >&2
  exit 2
fi

exec python3 "$REPO/scripts/plan_and_generate.py" "$@"
