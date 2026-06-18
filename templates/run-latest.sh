#!/usr/bin/env bash
# Stable launcher for the whetstone daily cron.
#
# This file lives at ~/.whetstone/run-latest.sh — a fixed path that never
# changes across plugin updates. The launchd job points HERE. At run time
# it resolves the highest installed plugin version from the plugin cache
# and execs that version's generator. So `/plugin update` (or
# `/whetstone:update`) drops a new version dir and the very next cron run
# picks it up automatically — no plist rewrite, no manual reinstall.
#
# Override WHETSTONE_REPO to force a specific copy (e.g. a dev clone).

set -euo pipefail

if [[ -n "${WHETSTONE_REPO:-}" ]]; then
  exec "$WHETSTONE_REPO/scripts/generate-lesson.sh" "$@"
fi

CACHE="$HOME/.claude/plugins/cache/n33kos/whetstone"
LATEST="$(ls -d "$CACHE"/*/ 2>/dev/null | sort -V | tail -1)"

if [[ -z "$LATEST" ]]; then
  echo "whetstone: no installed plugin version found under $CACHE" >&2
  echo "whetstone: install via '/plugin install whetstone@n33kos' or set WHETSTONE_REPO." >&2
  exit 2
fi

LATEST="${LATEST%/}"
export WHETSTONE_REPO="$LATEST"
exec "$LATEST/scripts/generate-lesson.sh" "$@"
