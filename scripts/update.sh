#!/usr/bin/env bash
# whetstone update — pull the latest plugin version and refresh runtime.
#
# Invoked by the /whetstone:update skill. Does everything under the hood:
#   1. Refresh the n33kos marketplace.
#   2. Update the whetstone plugin to its latest version (new cache dir).
#   3. Run the newly-installed version's install.sh to refresh shared
#      deps, backfill state, and re-verify the single launchd job.
#
# The daily cron launcher (~/.whetstone/run-latest.sh) resolves the
# latest installed version at run time, so the next scheduled run adopts
# the update automatically regardless. This script just makes it
# immediate and refreshes deps.

set -euo pipefail

CACHE="$HOME/.claude/plugins/cache/n33kos/whetstone"

say() { printf '\033[1;36m›\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

CLAUDE_BIN=""
for c in "$(command -v claude || true)" "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
  if [[ -n "$c" && -x "$c" ]]; then CLAUDE_BIN="$c"; break; fi
done
[[ -n "$CLAUDE_BIN" ]] || die "claude CLI not found."

say "Refreshing n33kos marketplace"
"$CLAUDE_BIN" plugin marketplace update n33kos 2>/dev/null || say "(marketplace refresh skipped)"

say "Updating whetstone plugin to latest"
"$CLAUDE_BIN" plugin update whetstone@n33kos || die "plugin update failed."

LATEST="$(ls -d "$CACHE"/*/ 2>/dev/null | sort -V | tail -1)"
[[ -n "$LATEST" ]] || die "No installed version found under $CACHE after update."
LATEST="${LATEST%/}"

say "Refreshing runtime from $LATEST"
exec "$LATEST/scripts/install.sh"
