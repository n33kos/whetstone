#!/usr/bin/env bash
# whetstone uninstall — remove the launchd plist and ~/.whetstone state.
#
# Does NOT remove the repo at ~/whetstone/ itself.
# Asks for confirmation before deleting state (lessons + knowledge map).

set -euo pipefail

STATE="${WHETSTONE_STATE:-$HOME/.whetstone}"
LABEL="com.whetstone.daily"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

say() { printf '\033[1;36m›\033[0m %s\n' "$*"; }

if [[ -f "$PLIST" ]]; then
  say "Unloading and removing launchd plist"
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
fi

if [[ -d "$STATE" ]]; then
  printf 'Delete state directory %s? This removes all lessons and the knowledge map. [y/N] ' "$STATE"
  read -r reply
  case "$reply" in
    y|Y|yes|YES)
      rm -rf "$STATE"
      say "Removed $STATE"
      ;;
    *)
      say "Left $STATE in place."
      ;;
  esac
fi

say "Uninstall complete."
